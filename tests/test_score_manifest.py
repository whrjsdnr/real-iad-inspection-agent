import csv
import pytest
from score_batch import load_manifest

def test_duplicate_missing_and_mixed_split(tmp_path):
 p=tmp_path/'m.csv'
 def save(rows):
  with p.open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=['product_id','category','camera','truth','split']);w.writeheader();w.writerows(rows)
 rows=[dict(product_id='cat/NG/QS/S1',category='cat',camera=f'C{i}',truth='defect',split='test') for i in range(1,6)]
 save(rows);assert len(load_manifest(p))==1
 save(rows[:-1])
 with pytest.raises(ValueError):load_manifest(p)
 rows[-1]['split']='train';save(rows)
 with pytest.raises(ValueError):load_manifest(p)
