"""Export only public cached GT responses; leave original MV assets untouched."""
import asyncio,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.ground_truth_api import catalog,ground_truth,index
from app.shared_data_api import clean
ROOT=Path(__file__).resolve().parents[1];KIT=ROOT/'team_integration_kit'
async def main():
    data=await catalog();out=KIT/'heatmaps';out.mkdir(exist_ok=True)
    for entry in data['entries']:
        if entry['product_id']:continue
        response=await ground_truth(entry['item'],entry['view'],'train',None,None)
        (out/f'{entry["item"]}-{entry["view"]}-train.json').write_text(json.dumps(clean(response),separators=(',',':'),ensure_ascii=False,allow_nan=False))
    (KIT/'HEATMAP_CATALOG.json').write_text(json.dumps(data,indent=2,ensure_ascii=False))
    (KIT/'samples/mv_source_validation.json').write_text(json.dumps({key:value for key,value in index().items() if key!='entries'},indent=2,ensure_ascii=False))
    print('Exported 150 existing numerical item-view Train NG maps; no Test/Validation or physical UV maps invented.')
asyncio.run(main())
