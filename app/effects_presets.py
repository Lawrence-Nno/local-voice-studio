"""Validated local named effect settings; audio files are never included."""
import math
from pathlib import Path
from .storage import DATA,atomic_json,read_json

BUILTINS={
    'Normal voice':dict(speed=1,pitch=0,reverb=0,radio=False),
    'Subtle reverb':dict(speed=1,pitch=0,reverb=.15,radio=False),
    'Slightly faster narration':dict(speed=1.1,pitch=0,reverb=0,radio=False),
    'Radio voice':dict(speed=1,pitch=0,reverb=0,radio=True),
}


def validate_settings(settings):
    if not isinstance(settings,dict) or set(settings) not in ({'speed','pitch','reverb','radio'},{'speed','pitch','reverb','radio','formant'}):
        raise ValueError('A preset must contain speed, pitch, reverb and radio settings.')
    for key,low,high in (('speed',.5,2),('pitch',-12,12),('reverb',0,1)):
        value=settings[key]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high:
            raise ValueError('Invalid '+key+' setting in preset.')
    if not isinstance(settings['radio'],bool):
        raise ValueError('Radio setting must be true or false.')
    if 'formant' in settings and not isinstance(settings['formant'],bool):
        raise ValueError('Vocal character preservation must be true or false.')
    return dict(settings)


def validate_name(name):
    if not isinstance(name,str) or not name.strip() or len(name.strip())>80 or any(ord(c)<32 for c in name):
        raise ValueError('Use a non-empty preset name up to 80 characters, without control characters.')
    name=name.strip()
    if name.casefold() in {key.casefold() for key in BUILTINS}:
        raise ValueError('Choose a different name; starter presets cannot be overwritten.')
    return name


class EffectsPresets:
    def __init__(self,path=None):
        self.path=Path(path) if path else DATA/'effects-presets.json'
        document=read_json(self.path,{'version':1,'presets':{}})
        if document.get('version')!=1 or not isinstance(document.get('presets'),dict):
            raise ValueError('Unsupported effects preset file. Restore it from backup before saving presets.')
        self.custom={}
        for name,settings in document['presets'].items():
            name=validate_name(name)
            if name.casefold() in {key.casefold() for key in self.custom}:
                raise ValueError('Duplicate preset names in saved file.')
            self.custom[name]=validate_settings(settings)

    def all(self):
        return {**{name:dict(settings) for name,settings in BUILTINS.items()},
                **{name:dict(self.custom[name]) for name in sorted(self.custom,key=str.casefold)}}

    def save(self,name,settings,replace=False):
        name=validate_name(name)
        settings=validate_settings(settings)
        existing=next((key for key in self.custom if key.casefold()==name.casefold()),None)
        if existing and not replace:
            raise ValueError('That preset already exists. Select it and use Update selected instead.')
        if replace and not existing:
            raise ValueError('Select one of your saved presets to update.')
        name=existing or name
        updated={**self.custom,name:settings}
        atomic_json(self.path,{'version':1,'presets':updated})
        self.custom=updated
        return name

    def delete(self,name):
        if name not in self.custom:
            raise ValueError('Only your saved presets can be deleted.')
        updated={key:value for key,value in self.custom.items() if key!=name}
        atomic_json(self.path,{'version':1,'presets':updated})
        self.custom=updated
