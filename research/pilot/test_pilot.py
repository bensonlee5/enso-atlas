import json, tempfile, unittest
from pathlib import Path
import numpy as np
import pandas as pd
from train_pilot import load_split, neural_json_predict, RAW, OBS
DATA=Path(__file__).parent/'data/pairs.csv'
class IntegrityTests(unittest.TestCase):
    def test_real_splits_and_purge(self):
        splits,purged,regions=load_split(DATA)
        self.assertEqual(len(regions),6)
        self.assertGreater(purged,0)
        self.assertTrue((splits['train'].init_date.dt.year<2015).all())
        self.assertTrue(splits['validation'].init_date.dt.year.between(2015,2017).all())
        self.assertTrue((splits['test'].init_date.dt.year>=2018).all())
        for d in splits.values():
            self.assertTrue(((d.target_start-d.init_date).dt.days==15).all())
            self.assertTrue(((d.target_end-d.init_date).dt.days==28).all())
    def test_duplicates_rejected(self):
        d=pd.read_csv(DATA); d=pd.concat([d,d.iloc[:1]])
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'bad.csv'; d.to_csv(p,index=False)
            with self.assertRaisesRegex(ValueError,'Duplicate'): load_split(p)
    def test_overlapping_targets_rejected(self):
        d=pd.read_csv(DATA)
        d.loc[6,'init_date']='1999-01-14'; d.loc[6,'target_start']='1999-01-29'; d.loc[6,'target_end']='1999-02-11'
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'bad.csv'; d.to_csv(p,index=False)
            with self.assertRaisesRegex(ValueError,'Overlapping'): load_split(p)
    def test_saved_model_and_metrics(self):
        out=Path(__file__).parent/'run'
        if not (out/'model.json').exists(): self.skipTest('Training not yet run')
        artifact=json.loads((out/'model.json').read_text())
        report=json.loads((out/'report.json').read_text())
        splits,_,_=load_split(DATA); d=splits['test']
        pred=neural_json_predict(d,artifact)
        self.assertFalse(artifact['config']['enso_features'])
        self.assertTrue(np.isfinite(pred).all()); self.assertTrue((pred[:,1]>=0).all())
        for i,k in enumerate(['temperature_c','precipitation_14day_mm']):
            expected=np.sqrt(np.mean((d[OBS].to_numpy()[:,i]-pred[:,i])**2))
            self.assertAlmostEqual(report['metrics']['test']['overall']['neural_residual_no_enso'][k]['rmse'],expected,places=10)
if __name__=='__main__': unittest.main()
