"""Sequential offline jobs with per-file reporting and safe cancellation."""
import json
import subprocess
import tempfile
from pathlib import Path

from .storage import ROOT, atomic_json
from .converter_ui import EXTENSIONS


def run_batch(files, operation, settings, directory, interpreter, cancel, notify, continue_errors=True):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=False)
    rows=[{'source':str(path),'status':'Queued'} for path in files]
    report={'operation':operation,'settings':settings,'files':rows,'status':'Running'}
    def save():
        atomic_json(directory/'batch-report.json',report)
    save()
    process=None
    try:
        with (directory/'worker.log').open('a',encoding='utf-8') as log:
            for index,source in enumerate(files):
                if cancel.is_set():
                    break
                row=rows[index]
                row['status']='Running'
                notify(index,'Running',None)
                save()
                try:
                    with tempfile.TemporaryDirectory(dir=directory,prefix='work-') as temporary:
                        work=Path(temporary)
                        extension='.srt' if operation=='Subtitles' else '.wav' if operation=='Cleanup' else EXTENSIONS[settings['format_name']]
                        output=directory/(f'{index+1:03d}-'+Path(source).stem+extension)
                        intermediate=work/('result'+extension)
                        if operation=='Convert':
                            module='app.conversion_worker'
                            request={'source':str(source),'destination':str(intermediate),**settings}
                        elif operation=='Cleanup':
                            module='app.cleanup_worker'
                            request={'source':str(source),'destination':str(intermediate),'original':str(work/'original.wav'),**settings}
                        elif operation=='Subtitles':
                            module='app.subtitle_worker'
                            request={'mode':'transcribe','audio':str(source),**settings}
                        else:
                            raise ValueError('Unsupported batch operation.')
                        if not Path(source).is_file():
                            raise ValueError('Source file is missing.')
                        process=subprocess.Popen([str(interpreter),'-E','-s','-m',module],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
                        payload=json.dumps(request)+'\n'
                        while True:
                            if cancel.is_set():
                                process.terminate()
                                process.communicate()
                                break
                            try:
                                stdout,_=process.communicate(input=payload,timeout=.2)
                                break
                            except subprocess.TimeoutExpired:
                                payload=None
                        if cancel.is_set():
                            row['status']='Cancelled'
                            notify(index,'Cancelled',None)
                            break
                        messages=[json.loads(line) for line in stdout.splitlines() if line.strip()]
                        if not messages:
                            raise RuntimeError('Audio worker stopped without a result. See worker.log.')
                        result=messages[-1]
                        if operation=='Subtitles':
                            if 'error' in result:
                                raise ValueError(result['error'])
                            text=result['result']['srt']
                            if not text.strip():
                                raise ValueError('No speech was detected; no SRT was published.')
                            intermediate.write_text(text,encoding='utf-8')
                        elif not result.get('ok'):
                            raise ValueError(result.get('error','Audio worker failed.'))
                        if cancel.is_set():
                            row['status']='Cancelled'
                            notify(index,'Cancelled',None)
                            break
                        intermediate.replace(output)
                        row.update(status='Completed',output=str(output))
                        notify(index,'Completed',str(output))
                except Exception as exc:
                    row.update(status='Failed',error=str(exc))
                    notify(index,'Failed',str(exc))
                    if not continue_errors:
                        break
                finally:
                    if process and process.poll() is None:
                        process.terminate()
                        process.communicate()
                    process=None
                    save()
        for index,row in enumerate(rows):
            if row['status']=='Queued':
                row['status']='Cancelled' if cancel.is_set() else 'Skipped'
                notify(index,row['status'],None)
        report['status']='Cancelled' if cancel.is_set() else 'Finished'
        save()
        return report
    finally:
        if process and process.poll() is None:
            process.terminate()
            process.communicate()
