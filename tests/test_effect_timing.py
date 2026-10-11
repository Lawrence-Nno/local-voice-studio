import math
import unittest
import tempfile
from pathlib import Path
from app.effect_timing import timing_plan
from app.effects_presets import validate_settings
from app.effects_presets import EffectsPresets


class TimingTests(unittest.TestCase):
    def test_duration_includes_reverb_tail(self):
        speed,frames,mapping=timing_plan(48000,24000,time_mode='Fit duration',target_duration=3,reverb=.2)
        self.assertEqual(frames,57600)
        self.assertAlmostEqual(speed,2/2.4)
        self.assertIsNone(mapping)
        for target in (.1,float('nan'),10):
            with self.assertRaises(ValueError):
                timing_plan(48000,24000,time_mode='Fit duration',target_duration=target)

    def test_ramp_integral_monotonic_and_constant(self):
        speed,frames,mapping=timing_plan(48000,24000,speed=.5,time_mode='Gradual speed',end_speed=2)
        self.assertEqual(frames,round(48000*math.log(4)/1.5))
        self.assertEqual(mapping[0],(0,0))
        self.assertEqual(mapping[-1],(48000,frames))
        self.assertTrue(all(a[0]<b[0] and a[1]<b[1] for a,b in zip(mapping,mapping[1:])))
        self.assertGreater((mapping[1][1]-mapping[0][1])/(mapping[1][0]-mapping[0][0]),
                           (mapping[-1][1]-mapping[-2][1])/(mapping[-1][0]-mapping[-2][0]))
        self.assertEqual(timing_plan(48000,24000,speed=.8,time_mode='Gradual speed',end_speed=.8),(.8,60000,None))

    def test_preset_validation(self):
        settings=dict(speed=1,pitch=0,reverb=0,radio=False,time_mode='Gradual speed',target_duration=10,end_speed=.8)
        self.assertEqual(validate_settings(settings),settings)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'presets.json'
            store=EffectsPresets(path)
            store.save('Slow to fast',settings)
            self.assertEqual(EffectsPresets(path).all()['Slow to fast'],settings)
        settings['end_speed']=float('nan')
        with self.assertRaises(ValueError): validate_settings(settings)
