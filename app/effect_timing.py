"""Validate timing modes and build sample-accurate Rubber Band keyframes."""
import math

MODES=('Constant speed','Fit duration','Gradual speed')


def timing_plan(frames, rate, speed=1, time_mode='Constant speed', target_duration=10,
                end_speed=1, reverb=0):
    if time_mode not in MODES:
        raise ValueError('Choose a valid speed mode.')
    if not math.isfinite(speed) or not .5<=speed<=2:
        raise ValueError('Starting speed must be between 0.5x and 2x.')
    if time_mode=='Fit duration':
        if not math.isfinite(target_duration) or not 0<target_duration<=1200.6:
            raise ValueError('Enter a positive final duration, up to 1200.6 seconds.')
        final_frames=round(target_duration*rate)
        tail=round(.6*rate) if reverb else 0
        output_frames=final_frames-tail
        if output_frames<=0 or not .5<=frames/output_frames<=2:
            raise ValueError('Target duration needs speed outside 0.5–2x. Choose a duration between half and twice the source length, plus 0.6s if reverb is enabled.')
        return frames/output_frames, output_frames, None
    if time_mode=='Gradual speed':
        if not math.isfinite(end_speed) or not .5<=end_speed<=2:
            raise ValueError('Ending speed must be between 0.5x and 2x.')
        difference=end_speed-speed
        if abs(difference)<1e-10:
            return speed, round(frames/speed), None
        def target(position):
            return round(frames*math.log1p(difference*position/(frames*speed))/difference)
        positions=list(range(0,frames,max(1,round(rate*.05))))+[frames]
        mapping=[(position,target(position)) for position in positions]
        output_frames=mapping[-1][1]
        return frames/output_frames, output_frames, mapping
    return speed, round(frames/speed), None
