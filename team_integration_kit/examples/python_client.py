"""Standard-library read client. Set TEAM_API_URL and private TEAM_ACCESS_TOKEN."""
import json,os
from urllib.parse import urlencode
from urllib.request import Request,urlopen

class InspectionClient:
    def __init__(self,base_url,token):self.base_url=base_url.rstrip('/');self.token=token
    def get(self,path,**params):
        url=self.base_url+path+('?' + urlencode(params) if params else '')
        request=Request(url,headers={'Authorization':'Bearer '+self.token})
        with urlopen(request,timeout=15) as response:return json.load(response)

if __name__=='__main__':
    client=InspectionClient(os.environ['TEAM_API_URL'],os.environ['TEAM_ACCESS_TOKEN'])
    manifest=client.get('/sharing/manifest')
    print('items',len(manifest['items']),'products',manifest['products'],'views',manifest['views'])
    rows=client.get('/products',item='toothbrush',limit=2)
    print('products returned',len(rows['products']))
    grid=client.get('/parts/spatial-heatmap',item='toothbrush',product_id='toothbrush/NG/CH/S0001',view='C1',region_id='bristle',model='rt',resolution=32,method='confidence_area')
    assert grid['grid_width']==grid['grid_height']==32 and len(grid['values'])==1024
    print('spatial grid',grid['grid_width'],grid['grid_height'],'distinct values',len(set(grid['values'])))


def ground_truth(client,item='toothbrush',view='C1'):
    return client.get('/heatmaps/ground-truth',item=item,view=view,split='train')
