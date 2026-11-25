"""품목별 부위 ROI 템플릿 데이터 — 실제 데이터셋 원본 이미지를 열어 확인한 폴리곤만 등록.

작성 규칙 (작업지시서 준수):
- 실제로 촬영된 구조만 부위로 등록한다 (촬영 범위 밖 부위는 만들지 않는다).
- 폴리곤은 원본 이미지 픽셀 좌표(전 품목 1024x1024)이며, 참조 이미지와
  프레이밍 확인 이미지(다른 제품)를 반드시 함께 둔다.
- 칫솔 손잡이는 사용자 지시로 등록하지 않는다 (기존 결정 유지).
"""

TEMPLATES = [
    # ---------------------------------------------------------------- toothbrush
    {
        'item': 'toothbrush', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/toothbrush/OK/S0001/toothbrush_0001_OK_C1_20230911162901.jpg',
        'regions': [
            {'region_id': 'bristle', 'label': '헤드 / 칫솔모',
             'polygon': [[140, 55], [825, 55], [825, 700], [140, 700]]},
        ],
        'coverage': {'neck': 'not_annotated'},
        'framing_checks': [
            '/home/geonug/MV/dataset/toothbrush/OK/S0002/toothbrush_0002_OK_C1_20230911162955.jpg',
            '/home/geonug/MV/dataset/toothbrush/NG/CH/S0001/toothbrush_0001_NG_CH_C1_20230912143447.jpg',
        ],
        'note': '헤드 상단 확대; C1은 정면에서 헤드가 가로로 배치(손잡이 우측). 2026-11-24 육안 확인.',
    },
    {
        'item': 'toothbrush', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/toothbrush/OK/S0001/toothbrush_0001_OK_C2_20230911162901.jpg',
        'regions': [
            {'region_id': 'bristle', 'label': '헤드 / 칫솔모',
             'polygon': [[150, 170], [810, 170], [810, 810], [150, 810]]},
        ],
        'coverage': {'neck': 'not_annotated'},
        'framing_checks': [
            '/home/geonug/MV/dataset/toothbrush/NG/CH/S0001/toothbrush_0001_NG_CH_C2_20230912143447.jpg',
        ],
        'note': '측면; 칫솔모가 위로 솟음.',
    },
    {
        'item': 'toothbrush', 'camera': 'C3', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/toothbrush/OK/S0001/toothbrush_0001_OK_C3_20230911162901.jpg',
        'regions': [
            {'region_id': 'bristle', 'label': '헤드 / 칫솔모',
             'polygon': [[130, 195], [450, 195], [515, 560], [475, 1024], [235, 1024], [235, 710], [130, 500]]},
        ],
        'coverage': {'neck': 'not_annotated'},
        'framing_checks': [
            '/home/geonug/MV/dataset/toothbrush/NG/CH/S0001/toothbrush_0001_NG_CH_C3_20230912143447.jpg',
        ],
        'note': '헤드 정면(끝에서); 칫솔모가 세로로 보임.',
    },
    {
        'item': 'toothbrush', 'camera': 'C4', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/toothbrush/OK/S0001/toothbrush_0001_OK_C4_20230911162901.jpg',
        'regions': [
            {'region_id': 'bristle', 'label': '헤드 / 칫솔모',
             'polygon': [[215, 160], [775, 160], [810, 800], [210, 800]]},
        ],
        'coverage': {'neck': 'not_annotated'},
        'framing_checks': [
            '/home/geonug/MV/dataset/toothbrush/NG/CH/S0001/toothbrush_0001_NG_CH_C4_20230912143447.jpg',
        ],
        'note': '측면(반대 방향); 손잡이가 좌측.',
    },
    {
        'item': 'toothbrush', 'camera': 'C5', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/toothbrush/OK/S0001/toothbrush_0001_OK_C5_20230911162901.jpg',
        'regions': [
            {'region_id': 'bristle', 'label': '헤드 / 칫솔모',
             'polygon': [[80, 110], [480, 110], [505, 530], [500, 950], [180, 950], [165, 650], [80, 500]]},
        ],
        'coverage': {'neck': 'not_annotated'},
        'framing_checks': [
            '/home/geonug/MV/dataset/toothbrush/NG/CH/S0001/toothbrush_0001_NG_CH_C5_20230912143447.jpg',
        ],
        'note': '윗면(경사); 목이 위로 보이나 손잡이는 화면 밖 — 사용자 지시로 미등록.',
    },
    # ---------------------------------------------------------------- audiojack
    {
        'item': 'audiojack', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/audiojack/OK/S0001/audiojack_0001_OK_C1_20231021130235.jpg',
        'regions': [
            {'region_id': 'housing', 'label': '커넥터 하우징',
             'polygon': [[290, 335], [855, 335], [855, 775], [290, 775]]},
            {'region_id': 'interface', 'label': '플러그 원통부',
             'polygon': [[182, 425], [298, 425], [298, 645], [182, 645]]},
            {'region_id': 'pins', 'label': '전기 접점',
             'polygon': [[330, 345], [630, 345], [630, 740], [330, 740]]},
        ],
        'coverage': {},
        'framing_checks': [
            '/home/geonug/MV/dataset/audiojack/NG/BX/S0001/audiojack__0001_NG_BX_C1_20231023111538.jpg',
        ],
        'note': '상단 면; 원통형 플러그가 좌측, 우측에 접점 블록. 2026-11-24 육안 확인.',
    },
    {
        'item': 'audiojack', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/audiojack/OK/S0001/audiojack_0001_OK_C2_20231021130235.jpg',
        'regions': [
            {'region_id': 'housing', 'label': '커넥터 하우징',
             'polygon': [[305, 205], [850, 205], [850, 795], [305, 795]]},
            {'region_id': 'interface', 'label': '플러그 원통부',
             'polygon': [[212, 448], [313, 448], [313, 642], [212, 642]]},
            {'region_id': 'pins', 'label': '전기 접점',
             'polygon': [[335, 210], [700, 210], [700, 605], [335, 605]]},
        ],
        'coverage': {},
        'framing_checks': [
            '/home/geonug/MV/dataset/audiojack/NG/BX/S0001/audiojack__0001_NG_BX_C2_20231023111538.jpg',
        ],
        'note': '상단 반대 각도.',
    },
    {
        'item': 'audiojack', 'camera': 'C3', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/audiojack/OK/S0001/audiojack_0001_OK_C3_20231021130235.jpg',
        'regions': [
            {'region_id': 'housing', 'label': '커넥터 하우징',
             'polygon': [[295, 235], [685, 235], [685, 845], [295, 845]]},
            {'region_id': 'interface', 'label': '플러그 원통부',
             'polygon': [[408, 178], [597, 178], [597, 252], [408, 252]]},
            {'region_id': 'pins', 'label': '전기 접점',
             'polygon': [[308, 245], [668, 245], [668, 535], [308, 535]]},
        ],
        'coverage': {},
        'framing_checks': [
            '/home/geonug/MV/dataset/audiojack/NG/BX/S0001/audiojack__0001_NG_BX_C3_20231023111538.jpg',
        ],
        'note': '측면; 다리(핀)가 위로.',
    },
    {
        'item': 'audiojack', 'camera': 'C4', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/audiojack/OK/S0001/audiojack_0001_OK_C4_20231021130235.jpg',
        'regions': [
            {'region_id': 'housing', 'label': '커넥터 하우징',
             'polygon': [[320, 275], [848, 275], [848, 848], [320, 848]]},
            {'region_id': 'interface', 'label': '플러그 원통부',
             'polygon': [[218, 505], [318, 505], [318, 702], [218, 702]]},
            {'region_id': 'pins', 'label': '전기 접점',
             'polygon': [[350, 285], [640, 285], [640, 620], [350, 620]]},
        ],
        'coverage': {},
        'framing_checks': [
            '/home/geonug/MV/dataset/audiojack/NG/BX/S0001/audiojack__0001_NG_BX_C4_20231023111538.jpg',
        ],
        'note': '상단(또 다른 각도).',
    },
    {
        'item': 'audiojack', 'camera': 'C5', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/audiojack/OK/S0001/audiojack_0001_OK_C5_20231021130235.jpg',
        'regions': [
            {'region_id': 'housing', 'label': '커넥터 하우징',
             'polygon': [[358, 178], [708, 178], [708, 795], [358, 795]]},
            {'region_id': 'interface', 'label': '플러그 원통부',
             'polygon': [[425, 668], [632, 668], [632, 862], [425, 862]]},
            {'region_id': 'pins', 'label': '전기 접점',
             'polygon': [[370, 185], [672, 185], [672, 520], [370, 520]]},
        ],
        'coverage': {},
        'framing_checks': [
            '/home/geonug/MV/dataset/audiojack/NG/BX/S0001/audiojack__0001_NG_BX_C5_20231023111538.jpg',
        ],
        'note': '후면; 플러그 구멍이 아래쪽.',
    },
    # ---------------------------------------------------------------- bottle_cap
    {
        'item': 'bottle_cap', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/bottle_cap/OK/S0001/bottle_cap_0001_OK_C1_20230925164816.jpg',
        'regions': [
            {'region_id': 'body', 'label': '상단 면',
             'polygon': [[842, 462], [746, 695], [512, 792], [278, 695], [182, 462], [278, 229], [512, 132], [746, 229]]},
        ],
        'coverage': {'ribs': 'side_view_only'},
        'framing_checks': ['/home/geonug/MV/dataset/bottle_cap/NG/AK/S0001/bottle_cap_0001_NG_AK_C1_20230926102621.jpg'],
        'note': '정상 뚜껑 상단 면 전체(겉니 리브는 측면에서만 분리). 2026-11-24 육안 확인.',
    },
    {
        'item': 'bottle_cap', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/bottle_cap/OK/S0001/bottle_cap_0001_OK_C2_20230925164816.jpg',
        'regions': [
            {'region_id': 'body', 'label': '상단 면',
             'polygon': [[200, 240], [800, 240], [800, 460], [200, 460]]},
            {'region_id': 'ribs', 'label': '겉니 리브',
             'polygon': [[205, 460], [795, 460], [795, 725], [205, 725]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/bottle_cap/NG/AK/S0001/bottle_cap_0001_NG_AK_C2_20230926102621.jpg'],
        'note': '측면; 상단 면과 겉니 밴드로 분할(중첩 없음).',
    },
    {
        'item': 'bottle_cap', 'camera': 'C3', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/bottle_cap/OK/S0001/bottle_cap_0001_OK_C3_20230925164816.jpg',
        'regions': [
            {'region_id': 'body', 'label': '상단 면',
             'polygon': [[190, 245], [805, 245], [805, 465], [190, 465]]},
            {'region_id': 'ribs', 'label': '겉니 리브',
             'polygon': [[195, 470], [800, 470], [800, 740], [195, 740]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/bottle_cap/NG/AK/S0001/bottle_cap_0001_NG_AK_C3_20230926102621.jpg'],
        'note': '측면(다른 각도).',
    },
    {
        'item': 'button_battery', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/button_battery/OK/S0001/button_battery_0001_OK_C1_20230920162602.jpg',
        'regions': [
            {'region_id': 'body', 'label': '상단 면',
             'polygon': [[825, 462], [730, 760], [525, 882], [320, 760], [225, 462], [320, 164], [525, 42], [730, 164]]},
        ],
        'coverage': {'rim': 'side_view_only'},
        'framing_checks': ['/home/geonug/MV/dataset/button_battery/NG/AK/S0001/button_battery_0001_NG_AK_C1_20230922102047.jpg'],
        'note': '단추전지 상단(+ 표기면). 2026-11-24 육안 확인.',
    },
    {
        'item': 'button_battery', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/button_battery/OK/S0001/button_battery_0001_OK_C2_20230920162602.jpg',
        'regions': [
            {'region_id': 'body', 'label': '상단 면',
             'polygon': [[168, 158], [892, 158], [892, 505], [168, 505]]},
            {'region_id': 'rim', 'label': '측면 테두리',
             'polygon': [[172, 505], [888, 505], [888, 700], [172, 700]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/button_battery/NG/AK/S0001/button_battery_0001_NG_AK_C2_20230922102047.jpg'],
        'note': '측면; 상단 면과 측벽으로 분할.',
    },
    {
        'item': 'button_battery', 'camera': 'C3', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/button_battery/OK/S0001/button_battery_0001_OK_C3_20230920162602.jpg',
        'regions': [
            {'region_id': 'body', 'label': '상단 면',
             'polygon': [[152, 252], [868, 252], [868, 608], [152, 608]]},
            {'region_id': 'rim', 'label': '측면 테두리',
             'polygon': [[158, 608], [862, 608], [862, 762], [158, 762]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/button_battery/NG/AK/S0001/button_battery_0001_NG_AK_C3_20230922102047.jpg'],
        'note': '측면(반대 각도).',
    },
    {
        'item': 'end_cap', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/end_cap/OK/S0001/end_cap_0001_OK_C1_20231009173002.jpg',
        'regions': [
            {'region_id': 'body', 'label': '후면 커버',
             'polygon': [[135, 205], [830, 205], [830, 900], [135, 900]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/end_cap/NG/HS/S0001/end_cap_0001_NG_HS_C1_20231011091647.jpg'],
        'note': '사각 엔드캡 후면(평면). 중앙 보스는 전면(C2/C3)에서 별도 구조 — 3D 부위는 body 하나라 전면/후면 모두 body로 등록. 2026-11-24 육안 확인.',
    },
    {
        'item': 'end_cap', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/end_cap/OK/S0001/end_cap_0001_OK_C2_20231009173002.jpg',
        'regions': [
            {'region_id': 'body', 'label': '본체(보스 면)',
             'polygon': [[85, 175], [890, 175], [890, 780], [85, 780]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/end_cap/NG/HS/S0001/end_cap_0001_NG_HS_C2_20231011091647.jpg'],
        'note': '전면; 원통 보스 돌출.',
    },
    {
        'item': 'end_cap', 'camera': 'C3', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/end_cap/OK/S0001/end_cap_0001_OK_C3_20231009173002.jpg',
        'regions': [
            {'region_id': 'body', 'label': '본체(보스 면)',
             'polygon': [[130, 175], [950, 175], [950, 785], [130, 785]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/end_cap/NG/HS/S0001/end_cap_0001_NG_HS_C3_20231011091647.jpg'],
        'note': '전면(다른 각도).',
    },
    {
        'item': 'eraser', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/eraser/OK/S0001/eraser_0001_OK_C1_20231005101953.jpg',
        'regions': [
            {'region_id': 'body', 'label': '본체',
             'polygon': [[190, 295], [825, 295], [825, 745], [190, 745]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/eraser/NG/AK/S0001/eraser_0001_NG_AK_C1_20231005142556.jpg'],
        'note': '지우기 블록 전체. 2026-11-24 육안 확인.',
    },
    {
        'item': 'eraser', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/eraser/OK/S0001/eraser_0001_OK_C2_20231005101953.jpg',
        'regions': [
            {'region_id': 'body', 'label': '본체',
             'polygon': [[320, 210], [780, 210], [780, 800], [320, 800]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/eraser/NG/AK/S0001/eraser_0001_NG_AK_C2_20231005142556.jpg'],
        'note': '측면.',
    },
    # ---------------------------------------------------------------- fire_hood
    {
        'item': 'fire_hood', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/fire_hood/OK/S0001/fire_hood_0001_OK_C1_20230927151421.jpg',
        'regions': [
            {'region_id': 'body', 'label': '상단 면',
             'polygon': [[900, 480], [785, 755], [510, 870], [235, 755], [120, 480], [235, 205], [510, 90], [785, 205]]},
        ],
        'coverage': {'rim': 'side_view_only'},
        'framing_checks': ['/home/geonug/MV/dataset/fire_hood/NG/AK/S0001/fire_hood_0001_NG_AK_C1_20230928170842.jpg'],
        'note': '원통 나문 후드 상단. 2026-11-24 육안 확인.',
    },
    {
        'item': 'fire_hood', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/fire_hood/OK/S0001/fire_hood_0001_OK_C2_20230927151421.jpg',
        'regions': [
            {'region_id': 'body', 'label': '상단 면',
             'polygon': [[262, 142], [793, 142], [793, 505], [262, 505]]},
            {'region_id': 'rim', 'label': '측면 벽',
             'polygon': [[270, 500], [785, 500], [785, 895], [270, 895]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/fire_hood/NG/AK/S0001/fire_hood_0001_NG_AK_C2_20230928170842.jpg'],
        'note': '측면.',
    },
    # ---------------------------------------------------------------- mint
    {
        'item': 'mint', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/mint/OK/S0002/mint_0002_OK_C1_20230908131600.jpg',
        'regions': [
            {'region_id': 'body', 'label': '상단 면(문양)',
             'polygon': [[960, 478], [835, 779], [535, 903], [235, 779], [110, 478], [235, 177], [535, 53], [835, 177]]},
        ],
        'coverage': {'rim': 'side_view_only'},
        'framing_checks': ['/home/geonug/MV/dataset/mint/NG/QS/S0001/mint_0001_NG_QS_C1_20230908175027.jpg'],
        'note': '민트 캔디형 링 상단(양각 문양). 2026-11-24 육안 확인.',
    },
    {
        'item': 'mint', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/mint/OK/S0002/mint_0002_OK_C2_20230908131600.jpg',
        'regions': [
            {'region_id': 'body', 'label': '상단 면',
             'polygon': [[120, 290], [935, 290], [935, 600], [120, 600]]},
            {'region_id': 'rim', 'label': '측면 벽',
             'polygon': [[125, 600], [930, 600], [930, 880], [125, 880]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/mint/NG/QS/S0001/mint_0001_NG_QS_C2_20230908175027.jpg'],
        'note': '측면.',
    },
    # ---------------------------------------------------------------- mounts
    {
        'item': 'mounts', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/mounts/OK/S0001/mounts_0001_OK_C1_20231009090955.jpg',
        'regions': [
            {'region_id': 'body', 'label': '본체(보스 면)',
             'polygon': [[158, 268], [868, 268], [868, 782], [158, 782]]},
        ],
        'coverage': {'rails': 'side_view_only'},
        'framing_checks': ['/home/geonug/MV/dataset/mounts/NG/AK/S0001/mounts_0001_NG_AK_C1_20231009134637.jpg'],
        'note': '백색 마운트 상단; 좌우 그레이 패드는 레일이나 C1에서는 본체 면에 포함. 2026-11-24 육안 확인.',
    },
    {
        'item': 'mounts', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/mounts/OK/S0001/mounts_0001_OK_C2_20231009090955.jpg',
        'regions': [
            {'region_id': 'rails', 'label': '측면 레일',
             'polygons': [[[215, 165], [330, 165], [330, 862], [215, 862]],
                          [[648, 165], [760, 165], [760, 862], [648, 862]]]},
            {'region_id': 'body', 'label': '가로 보스',
             'polygon': [[332, 540], [648, 540], [648, 755], [332, 755]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/mounts/NG/AK/S0001/mounts_0001_NG_AK_C2_20231009134637.jpg'],
        'note': '측면 H형; 좌우 벽=레일(2 폴리곤), 중앙 가로대=본체.',
    },
    # ---------------------------------------------------------------- pcb
    {
        'item': 'pcb', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/pcb/OK/S0001/pcb_0001_OK_C1_20231027155851.jpg',
        'regions': [
            {'region_id': 'contacts', 'label': 'USB 커넥터/접점',
             'polygon': [[183, 408], [392, 408], [392, 668], [183, 668]]},
            {'region_id': 'components', 'label': '실장 부품',
             'polygon': [[520, 330], [750, 330], [750, 625], [520, 625]]},
            {'region_id': 'substrate', 'label': '기판',
             'polygon': [[392, 212], [838, 212], [838, 823], [232, 823], [232, 668], [392, 668], [392, 625], [520, 625], [520, 330], [392, 330]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/pcb/NG/HS/S0001/pcb_0001_NG_HS_C1_20231028093757.jpg'],
        'note': '기판 상면; 기판/부품/커넥터 비중첩 분할. 2026-11-24 육안 확인.',
    },
    {
        'item': 'pcb', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/pcb/OK/S0001/pcb_0001_OK_C2_20231027155851.jpg',
        'regions': [
            {'region_id': 'contacts', 'label': 'USB 커넥터/접점',
             'polygon': [[200, 332], [402, 332], [402, 585], [200, 585]]},
            {'region_id': 'components', 'label': '실장 부품',
             'polygon': [[560, 350], [775, 350], [775, 625], [560, 625]]},
            {'region_id': 'substrate', 'label': '기판',
             'polygon': [[402, 240], [845, 240], [845, 780], [245, 780], [245, 585], [402, 585], [402, 625], [560, 625], [560, 350], [402, 350]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/pcb/NG/HS/S0001/pcb_0001_NG_HS_C2_20231028093757.jpg'],
        'note': '기판 반대 각도.',
    },
    # ---------------------------------------------------------------- phone_battery
    {
        'item': 'phone_battery', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/phone_battery/OK/S0001/phone_battery_0001_OK_C1_20230918094757.jpg',
        'regions': [
            {'region_id': 'contacts', 'label': '전극 패드',
             'polygon': [[778, 478], [858, 478], [858, 774], [778, 774]]},
            {'region_id': 'body', 'label': '본체(라벨)',
             'polygon': [[162, 140], [780, 140], [780, 478], [862, 478], [862, 774], [780, 774], [780, 888], [162, 888]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/phone_battery/NG/AK/S0001/phone_battery_0001_NG_AK_C1_20230919093604.jpg'],
        'note': '폰 배터리 라벨면; 우측 금색 3패드=접점. 2026-11-24 육안 확인.',
    },
    {
        'item': 'phone_battery', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/phone_battery/OK/S0001/phone_battery_0001_OK_C2_20230918094757.jpg',
        'regions': [
            {'region_id': 'body', 'label': '본체',
             'polygon': [[158, 312], [862, 312], [862, 882], [158, 882]]},
            {'region_id': 'contacts', 'label': '전극 패드',
             'polygon': [[768, 398], [852, 398], [852, 582], [768, 582]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/phone_battery/NG/AK/S0001/phone_battery_0001_NG_AK_C2_20230919093604.jpg'],
        'note': '측면(흐림); 접점부만 분리.',
    },
    {
        'item': 'eraser', 'camera': 'C3', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/eraser/OK/S0001/eraser_0001_OK_C3_20231005101953.jpg',
        'regions': [
            {'region_id': 'body', 'label': '본체',
             'polygon': [[220, 320], [805, 320], [805, 740], [220, 740]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/eraser/NG/AK/S0001/eraser_0001_NG_AK_C3_20231005142556.jpg'],
        'note': '측면(다른 각도).',
    },
    # ---------------------------------------------------------------- plastic_nut
    {
        'item': 'plastic_nut', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/plastic_nut/OK/S0001/plastic_nut_0001_OK_C1_20230930121449.jpg',
        'regions': [
            {'region_id': 'body', 'label': '플랜지 본체',
             'polygon': [[890, 505], [775, 772], [500, 895], [225, 772], [110, 505], [225, 238], [500, 115], [775, 238]]},
        ],
        'coverage': {'rim': 'not_separated_in_top_view'},
        'framing_checks': ['/home/geonug/MV/dataset/plastic_nut/NG/AK/S0001/plastic_nut_0001_NG_AK_C1_20231004132101.jpg'],
        'note': '6엽 플랜지 너트 상단; 중앙 홀 주변 링 분리는 미등록. 2026-11-24 육안 확인.',
    },
    {
        'item': 'plastic_nut', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/plastic_nut/OK/S0001/plastic_nut_0001_OK_C2_20230930121449.jpg',
        'regions': [
            {'region_id': 'body', 'label': '본체',
             'polygon': [[85, 100], [885, 100], [885, 900], [85, 900]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/plastic_nut/NG/AK/S0001/plastic_nut_0001_NG_AK_C2_20231004132101.jpg'],
        'note': '측면; 나사산 홀 낮부.',
    },
    # ---------------------------------------------------------------- plastic_plug
    {
        'item': 'plastic_plug', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/plastic_plug/OK/S0001/plastic_plug_0001_OK_C1_20230913130816.jpg',
        'regions': [
            {'region_id': 'body', 'label': '플랜지 상단',
             'polygon': [[855, 480], [774, 724], [485, 850], [196, 724], [115, 480], [196, 236], [485, 110], [774, 236]]},
        ],
        'coverage': {'collar': 'side_view_only'},
        'framing_checks': ['/home/geonug/MV/dataset/plastic_plug/NG/AK/S0001/plastic_plug_0001_NG_AK_C1_20230915171859.jpg'],
        'note': '레드 플러그 플랜지 상단. 2026-11-24 육안 확인.',
    },
    {
        'item': 'plastic_plug', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/plastic_plug/OK/S0001/plastic_plug_0001_OK_C2_20230913130816.jpg',
        'regions': [
            {'region_id': 'collar', 'label': '나사 칼라',
             'polygon': [[335, 200], [655, 200], [655, 610], [335, 610]]},
            {'region_id': 'body', 'label': '플랜지',
             'polygon': [[145, 320], [855, 320], [855, 870], [145, 870]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/plastic_plug/NG/AK/S0001/plastic_plug_0001_NG_AK_C2_20230915171859.jpg'],
        'note': '측면; 위 나사관=칼라, 아래 원판=플랜지.',
    },
    # ---------------------------------------------------------------- porcelain_doll
    {
        'item': 'porcelain_doll', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/porcelain_doll/OK/S0001/porcelain_doll_0001_OK_C1_20230915093055.jpg',
        'regions': [
            {'region_id': 'body', 'label': '링 본체',
             'polygon': [[800, 480], [709, 696], [495, 785], [281, 696], [190, 480], [281, 264], [495, 175], [709, 264]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/porcelain_doll/NG/CH/S0001/porcelain_doll_0001_NG_CH_C1_20230915180544.jpg'],
        'note': '도자기 링 스탠드 상단. 2026-11-24 육안 확인.',
    },
    {
        'item': 'porcelain_doll', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/porcelain_doll/OK/S0001/porcelain_doll_0001_OK_C2_20230915093055.jpg',
        'regions': [
            {'region_id': 'body', 'label': '링 본체',
             'polygon': [[250, 215], [820, 215], [820, 830], [250, 830]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/porcelain_doll/NG/CH/S0001/porcelain_doll_0001_NG_CH_C2_20230915180544.jpg'],
        'note': '측면; 입구 보임.',
    },
    # ---------------------------------------------------------------- regulator
    {
        'item': 'regulator', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/regulator/OK/S0001/regulator_0001_OK_C1_20231010141423.jpg',
        'regions': [
            {'region_id': 'hub', 'label': '중심 허브',
             'polygon': [[627, 505], [594, 589], [512, 620], [430, 589], [397, 505], [430, 421], [512, 390], [594, 421]]},
        ],
        'coverage': {'body': 'top_view_hub_only', 'rim': 'side_view_only', 'ribs': 'side_view_only'},
        'framing_checks': ['/home/geonug/MV/dataset/regulator/NG/AK/S0001/regulator_0001_NG_AK_C1_20231011142137.jpg'],
        'note': '레귤레이터 캡 상단; 중심 허브만 분리 등록. 2026-11-24 육안 확인.',
    },
    {
        'item': 'regulator', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/regulator/OK/S0001/regulator_0001_OK_C2_20231010141423.jpg',
        'regions': [
            {'region_id': 'ribs', 'label': '리브 벽(상하)',
             'polygons': [[[218, 352], [786, 352], [786, 622], [218, 622]],
                          [[224, 628], [782, 628], [782, 878], [224, 878]]]},
        ],
        'coverage': {'body': 'label_band_not_separated', 'rim': 'not_separated'},
        'framing_checks': ['/home/geonug/MV/dataset/regulator/NG/AK/S0001/regulator_0001_NG_AK_C2_20231011142137.jpg'],
        'note': '측면; 상하 리브 밴드(2 폴리곤).',
    },
    # ---------------------------------------------------------------- rolled_strip_base
    {
        'item': 'rolled_strip_base', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/rolled_strip_base/OK/S0001/rolled_strip_base_0001_OK_C1_20231012171250.jpg',
        'regions': [
            {'region_id': 'body', 'label': '베이스 상단',
             'polygon': [[208, 208], [838, 208], [838, 835], [208, 835]]},
        ],
        'coverage': {'ribs': 'not_separated_in_top_view'},
        'framing_checks': ['/home/geonug/MV/dataset/rolled_strip_base/NG/AK/S0001/rolled_strip_base_0001_NG_AK_C1_20231013155806.jpg'],
        'note': 'X보강 베이스 상면; 대각 리브 미분리. 2026-11-24 육안 확인.',
    },
    {
        'item': 'rolled_strip_base', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/rolled_strip_base/OK/S0001/rolled_strip_base_0001_OK_C2_20231012171250.jpg',
        'regions': [
            {'region_id': 'body', 'label': '베이스 본체',
             'polygon': [[142, 232], [848, 232], [848, 768], [142, 768]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/rolled_strip_base/NG/AK/S0001/rolled_strip_base_0001_NG_AK_C2_20231013155806.jpg'],
        'note': '측면; 슬롯 보임.',
    },
    # ---------------------------------------------------------------- sim_card_set
    {
        'item': 'sim_card_set', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/sim_card_set/OK/S0001/sim_card_set_0001_OK_C1_20230922140928.jpg',
        'regions': [
            {'region_id': 'body', 'label': '트레이 본체',
             'polygon': [[170, 168], [885, 168], [885, 738], [170, 738]]},
            {'region_id': 'tab', 'label': '연결 탭',
             'polygon': [[886, 150], [922, 150], [922, 812], [886, 812]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/sim_card_set/NG/CH/S0001/sim_card_set_0001_NG_CH_C1_20230923104439.jpg'],
        'note': 'SIM 트레이; 우측 세로 탭 분리. 2026-11-24 육안 확인.',
    },
    {
        'item': 'sim_card_set', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/sim_card_set/OK/S0001/sim_card_set_0001_OK_C2_20230922140928.jpg',
        'regions': [
            {'region_id': 'body', 'label': '트레이 본체',
             'polygon': [[150, 290], [848, 290], [848, 700], [150, 700]]},
            {'region_id': 'tab', 'label': '연결 탭',
             'polygon': [[848, 200], [880, 200], [880, 748], [848, 748]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/sim_card_set/NG/CH/S0001/sim_card_set_0001_NG_CH_C2_20230923104439.jpg'],
        'note': '측면 각도.',
    },
    # ---------------------------------------------------------------- switch
    {
        'item': 'switch', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/switch/OK/S0001/switch_0001_OK_C1_20231021104641.jpg',
        'regions': [
            {'region_id': 'housing', 'label': '스위치 하우징',
             'polygon': [[300, 200], [720, 200], [720, 795], [300, 795]]},
            {'region_id': 'interface', 'label': '로커 버튼',
             'polygon': [[742, 290], [927, 290], [927, 725], [742, 725]]},
            {'region_id': 'pins', 'label': '단자 핀',
             'polygon': [[80, 438], [302, 438], [302, 577], [80, 577]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/switch/NG/HS/S0001/switch_0001_NG_HS_C1_20231023091047.jpg'],
        'note': '로커 스위치 측면; 우측 빨간 로커, 좌측 단자 핀. 2026-11-24 육안 확인.',
    },
    {
        'item': 'switch', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/switch/OK/S0001/switch_0001_OK_C2_20231021104641.jpg',
        'regions': [
            {'region_id': 'housing', 'label': '스위치 하우징',
             'polygon': [[250, 235], [798, 235], [798, 815], [250, 815]]},
            {'region_id': 'pins', 'label': '단자 핀',
             'polygon': [[463, 595], [602, 595], [602, 890], [463, 890]]},
        ],
        'coverage': {'interface': 'not_visible'},
        'framing_checks': ['/home/geonug/MV/dataset/switch/NG/HS/S0001/switch_0001_NG_HS_C2_20231023091047.jpg'],
        'note': '후면; 하단 단자.',
    },
    # ---------------------------------------------------------------- tape
    {
        'item': 'tape', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/tape/OK/S0001/tape_0001_OK_C1_20231016105232.jpg',
        'regions': [
            {'region_id': 'body', 'label': '테이프 링',
             'polygon': [[882, 470], [772, 735], [507, 845], [242, 735], [132, 470], [242, 205], [507, 95], [772, 205]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/tape/NG/HS/S0001/tape_0001_NG_HS_C1_20231017161110.jpg'],
        'note': 'OPP 테이프 롤 상단. 2026-11-24 육안 확인.',
    },
    {
        'item': 'tape', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/tape/OK/S0001/tape_0001_OK_C2_20231016105232.jpg',
        'regions': [
            {'region_id': 'body', 'label': '테이프 롤',
             'polygon': [[83, 145], [928, 145], [928, 870], [83, 870]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/tape/NG/HS/S0001/tape_0001_NG_HS_C2_20231017161110.jpg'],
        'note': '측면.',
    },
    # ---------------------------------------------------------------- terminalblock
    {
        'item': 'terminalblock', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/terminalblock/OK/S0001/terminalblock_0001_OK_C1_20231019134717.jpg',
        'regions': [
            {'region_id': 'housing', 'label': '단자대 본체',
             'polygon': [[205, 320], [845, 320], [845, 720], [205, 720]]},
        ],
        'coverage': {'interface': 'not_separated', 'pins': 'not_separated'},
        'framing_checks': ['/home/geonug/MV/dataset/terminalblock/NG/AK/S0001/terminalblock_0001_NG_AK_C1_20231020130101.jpg'],
        'note': '단자대 정면; 6포트 — 미세 분리 없이 본체로 등록. 2026-11-24 육안 확인.',
    },
    {
        'item': 'terminalblock', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/terminalblock/OK/S0001/terminalblock_0001_OK_C2_20231019134717.jpg',
        'regions': [
            {'region_id': 'housing', 'label': '단자대 본체',
             'polygon': [[343, 205], [742, 205], [742, 785], [343, 785]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/terminalblock/NG/AK/S0001/terminalblock_0001_NG_AK_C2_20231020130101.jpg'],
        'note': '측면.',
    },
    # ---------------------------------------------------------------- toy
    {
        'item': 'toy', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/toy/OK/S0001/toy_0001_OK_C1_20230927102059.jpg',
        'regions': [
            {'region_id': 'surface', 'label': '장난감 하단 면',
             'polygon': [[825, 540], [718, 773], [495, 870], [272, 773], [165, 540], [272, 307], [495, 210], [718, 307]]},
        ],
        'coverage': {'edge': 'side_view_only', 'joint': 'not_separated'},
        'framing_checks': ['/home/geonug/MV/dataset/toy/NG/AK/S0001/toy_0001_NG_AK_C1_20230928100108.jpg'],
        'note': '햄버거 장난감 바닥면. 2026-11-24 육안 확인.',
    },
    {
        'item': 'toy', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/toy/OK/S0001/toy_0001_OK_C2_20230927102059.jpg',
        'regions': [
            {'region_id': 'surface', 'label': '번 윗면',
             'polygon': [[70, 380], [850, 380], [850, 760], [70, 760]]},
            {'region_id': 'edge', 'label': '채소 가장자리',
             'polygon': [[72, 760], [848, 760], [848, 872], [72, 872]]},
        ],
        'coverage': {'joint': 'not_separated'},
        'framing_checks': ['/home/geonug/MV/dataset/toy/NG/AK/S0001/toy_0001_NG_AK_C2_20230928100108.jpg'],
        'note': '윗면; 번/녹색 가장자리 분할.',
    },
    # ---------------------------------------------------------------- toy_brick
    {
        'item': 'toy_brick', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/toy_brick/OK/S0001/toy_brick_0001_OK_C1_20230917091117.jpg',
        'regions': [
            {'region_id': 'body', 'label': '블록 상단',
             'polygon': [[75, 145], [800, 145], [800, 970], [75, 970]]},
        ],
        'coverage': {'grooves': 'not_separated'},
        'framing_checks': ['/home/geonug/MV/dataset/toy_brick/NG/AK/S0001/toy_brick_0001_NG_AK_C1_20230917114449.jpg'],
        'note': '목제 블록 상면; 홈 미분리. 2026-11-24 육안 확인.',
    },
    {
        'item': 'toy_brick', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/toy_brick/OK/S0001/toy_brick_0001_OK_C2_20230917091117.jpg',
        'regions': [
            {'region_id': 'body', 'label': '블록 본체',
             'polygon': [[152, 102], [758, 102], [758, 940], [152, 940]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/toy_brick/NG/AK/S0001/toy_brick_0001_NG_AK_C2_20230917114449.jpg'],
        'note': '측면.',
    },
    # ---------------------------------------------------------------- transistor1
    {
        'item': 'transistor1', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/transistor1/OK/S0001/transistor1_0001_OK_C1_20230923145832.jpg',
        'regions': [
            {'region_id': 'contacts', 'label': '리드 핀(상하)',
             'polygons': [[[225, 232], [762, 232], [762, 318], [225, 318]],
                          [[228, 678], [768, 678], [768, 768], [228, 768]]]},
            {'region_id': 'substrate', 'label': 'IC 패키지',
             'polygon': [[212, 310], [774, 310], [774, 682], [212, 682]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/transistor1/NG/BX/S0001/transistor1_0001_NG_BX_C1_20230923194347.jpg'],
        'note': 'SOP IC 상면; 상하 리드 핀 2밴드. 2026-11-24 육안 확인.',
    },
    {
        'item': 'transistor1', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/transistor1/OK/S0001/transistor1_0001_OK_C2_20230923145832.jpg',
        'regions': [
            {'region_id': 'substrate', 'label': 'IC 패키지',
             'polygon': [[282, 288], [768, 288], [768, 735], [282, 735]]},
            {'region_id': 'contacts', 'label': '리드 핀(좌우)',
             'polygons': [[[168, 345], [285, 345], [285, 745], [168, 745]],
                          [[742, 345], [860, 345], [860, 750], [742, 750]]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/transistor1/NG/BX/S0001/transistor1_0001_NG_BX_C2_20230923194347.jpg'],
        'note': '측면; 좌우 핀.',
    },
    # ---------------------------------------------------------------- u_block
    {
        'item': 'u_block', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/u_block/OK/S0001/u_block_0001_OK_C1_20231005092626.jpg',
        'regions': [
            {'region_id': 'body', 'label': '링 본체',
             'polygon': [[805, 505], [711, 732], [485, 825], [259, 732], [165, 505], [259, 278], [485, 185], [711, 278]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/u_block/NG/CH/S0001/u_block_0001_NG_CH_C1_20231005140533.jpg'],
        'note': 'U블록 링 상단. 2026-11-24 육안 확인.',
    },
    {
        'item': 'u_block', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/u_block/OK/S0001/u_block_0001_OK_C2_20231005092626.jpg',
        'regions': [
            {'region_id': 'body', 'label': '컵 본체',
             'polygon': [[148, 160], [832, 160], [832, 945], [148, 945]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/u_block/NG/CH/S0001/u_block_0001_NG_CH_C2_20231005140533.jpg'],
        'note': '측면.',
    },
    # ---------------------------------------------------------------- usb
    {
        'item': 'usb', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/usb/OK/S0001/usb_0001_OK_C1_20231019140537.jpg',
        'regions': [
            {'region_id': 'housing', 'label': 'USB 쉴드 하우징',
             'polygon': [[192, 288], [818, 288], [818, 782], [192, 782]]},
            {'region_id': 'interface', 'label': '플러그 혀/접촉',
             'polygon': [[238, 338], [500, 338], [500, 680], [238, 680]]},
        ],
        'coverage': {'pins': 'not_separated'},
        'framing_checks': ['/home/geonug/MV/dataset/usb/NG/BX/S0001/usb_0001_NG_BX_C1_20231020105442.jpg'],
        'note': 'USB-A 리셉터클 상면. 2026-11-24 육안 확인.',
    },
    {
        'item': 'usb', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/usb/OK/S0001/usb_0001_OK_C2_20231019140537.jpg',
        'regions': [
            {'region_id': 'housing', 'label': 'USB 쉴드 하우징',
             'polygon': [[242, 300], [812, 300], [812, 772], [242, 772]]},
            {'region_id': 'interface', 'label': '날부 개구',
             'polygon': [[258, 352], [530, 352], [530, 650], [258, 650]]},
            {'region_id': 'pins', 'label': '상단 단자',
             'polygon': [[605, 215], [668, 215], [668, 315], [605, 315]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/usb/NG/BX/S0001/usb_0001_NG_BX_C2_20231020105442.jpg'],
        'note': '측면; 상단 단자 돌출.',
    },
    # ---------------------------------------------------------------- usb_adaptor
    {
        'item': 'usb_adaptor', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/usb_adaptor/OK/S0001/usb_adaptor_0001_OK_C1_20230923183216.jpg',
        'regions': [
            {'region_id': 'housing', 'label': '어댑터 본체',
             'polygon': [[335, 237], [903, 237], [903, 768], [335, 768]]},
            {'region_id': 'interface', 'label': 'USB-C 플러그',
             'polygon': [[70, 377], [337, 377], [337, 643], [70, 643]]},
        ],
        'coverage': {'pins': 'not_visible'},
        'framing_checks': ['/home/geonug/MV/dataset/usb_adaptor/NG/AK/S0001/usb_adaptor_0001_NG_AK_C1_20230925100402.jpg'],
        'note': 'USB-C 어댑터; 좌측 플러그 분리. 2026-11-24 육안 확인.',
    },
    {
        'item': 'usb_adaptor', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/usb_adaptor/OK/S0001/usb_adaptor_0001_OK_C2_20230923183216.jpg',
        'regions': [
            {'region_id': 'housing', 'label': '어댑터 본체',
             'polygon': [[378, 352], [872, 352], [872, 792], [378, 792]]},
            {'region_id': 'interface', 'label': 'USB-C 플러그',
             'polygon': [[115, 465], [380, 465], [380, 665], [115, 665]]},
        ],
        'coverage': {'pins': 'not_visible'},
        'framing_checks': ['/home/geonug/MV/dataset/usb_adaptor/NG/AK/S0001/usb_adaptor_0001_NG_AK_C2_20230925100402.jpg'],
        'note': '측면.',
    },
    # ---------------------------------------------------------------- vcpill
    {
        'item': 'vcpill', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/vcpill/OK/S0001/vcpill_0001_OK_C1_20230921111545.jpg',
        'regions': [
            {'region_id': 'body', 'label': '정제 상단',
             'polygon': [[762, 475], [660, 726], [407, 830], [154, 726], [52, 475], [154, 224], [407, 120], [660, 224]]},
        ],
        'coverage': {'rim': 'side_view_only'},
        'framing_checks': ['/home/geonug/MV/dataset/vcpill/NG/AK/S0001/vcpill_0001_NG_AK_C1_20230921183148.jpg'],
        'note': 'VC 정제 상면. 2026-11-24 육안 확인.',
    },
    {
        'item': 'vcpill', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/vcpill/OK/S0001/vcpill_0001_OK_C2_20230921111545.jpg',
        'regions': [
            {'region_id': 'body', 'label': '정제 본체',
             'polygon': [[47, 368], [688, 368], [688, 812], [47, 812]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/vcpill/NG/AK/S0001/vcpill_0001_NG_AK_C2_20230921183148.jpg'],
        'note': '측면.',
    },
    # ---------------------------------------------------------------- wooden_beads
    {
        'item': 'wooden_beads', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/wooden_beads/OK/S0001/wooden_beads_0001_OK_C1_20231013091008.jpg',
        'regions': [
            {'region_id': 'body', 'label': '구슬 본체',
             'polygon': [[830, 500], [732, 737], [495, 835], [258, 737], [160, 500], [258, 263], [495, 165], [732, 263]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/wooden_beads/NG/AK/S0001/wooden_beads_0001_NG_AK_C1_20231013145843.jpg'],
        'note': '원목 구슬. 2026-11-24 육안 확인.',
    },
    {
        'item': 'wooden_beads', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/wooden_beads/OK/S0001/wooden_beads_0001_OK_C2_20231013091008.jpg',
        'regions': [
            {'region_id': 'body', 'label': '구슬 본체',
             'polygon': [[168, 210], [838, 210], [838, 860], [168, 860]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/wooden_beads/NG/AK/S0001/wooden_beads_0001_NG_AK_C2_20231013145843.jpg'],
        'note': '측면.',
    },
    # ---------------------------------------------------------------- woodstick
    {
        'item': 'woodstick', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/woodstick/OK/S0001/woodstick_0001_OK_C1_20230925153625.jpg',
        'regions': [
            {'region_id': 'body', 'label': '원기둥 상단',
             'polygon': [[950, 480], [821, 789], [510, 920], [199, 789], [70, 480], [199, 171], [510, 40], [821, 171]]},
        ],
        'coverage': {'rim': 'side_view_only'},
        'framing_checks': ['/home/geonug/MV/dataset/woodstick/NG/AK/S0001/woodstick_0001_NG_AK_C1_20230926112105.jpg'],
        'note': '목제 원기둥 상단(격자 홈). 2026-11-24 육안 확인.',
    },
    {
        'item': 'woodstick', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/woodstick/OK/S0001/woodstick_0001_OK_C2_20230925153625.jpg',
        'regions': [
            {'region_id': 'body', 'label': '원기둥 본체',
             'polygon': [[142, 60], [928, 60], [928, 915], [142, 915]]},
        ],
        'coverage': {},
        'framing_checks': ['/home/geonug/MV/dataset/woodstick/NG/AK/S0001/woodstick_0001_NG_AK_C2_20230926112105.jpg'],
        'note': '측면.',
    },
    # ---------------------------------------------------------------- zipper
    {
        'item': 'zipper', 'camera': 'C1', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/zipper/OK/S0001/zipper_0001_OK_C1_20231007161245.jpg',
        'regions': [
            {'region_id': 'teeth', 'label': '코일 체인',
             'polygon': [[0, 445], [1024, 445], [1024, 545], [0, 545]]},
            {'region_id': 'tape', 'label': '양측 테이프',
             'polygons': [[[0, 398], [1024, 398], [1024, 448], [0, 448]],
                          [[0, 542], [1024, 542], [1024, 592], [0, 592]]]},
        ],
        'coverage': {'slider': 'not_in_frame'},
        'framing_checks': ['/home/geonug/MV/dataset/zipper/NG/BX/S0001/zipper_0001_NG_BX_C1_20231008164957.jpg'],
        'note': '코일 지퍼 스트립 정면; 슬라이더는 프레임 밖. 2026-11-24 육안 확인.',
    },
    {
        'item': 'zipper', 'camera': 'C2', 'image_size': [1024, 1024],
        'reference_image': '/home/geonug/MV/dataset/zipper/OK/S0001/zipper_0001_OK_C2_20231007161245.jpg',
        'regions': [
            {'region_id': 'teeth', 'label': '코일 체인',
             'polygon': [[0, 505], [1024, 505], [1024, 625], [0, 625]]},
            {'region_id': 'tape', 'label': '양측 테이프',
             'polygons': [[[0, 458], [1024, 458], [1024, 508], [0, 508]],
                          [[0, 628], [1024, 628], [1024, 682], [0, 682]]]},
        ],
        'coverage': {'slider': 'not_in_frame'},
        'framing_checks': ['/home/geonug/MV/dataset/zipper/NG/BX/S0001/zipper_0001_NG_BX_C2_20231008164957.jpg'],
        'note': '측면 각도.',
    },
]
