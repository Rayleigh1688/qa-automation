"""Display titles for existing ISOP-2022 result snapshots; no evidence mutation."""
RECORD_NAMES = {
    'bet-all':'按投注时间查询记录', 'settle-default':'按结算时间查询，默认排除体育',
    'node-1':'查询1线投注记录','node-2':'查询2线投注记录',
    'settle-node-1':'按结算时间查询1线记录','settle-node-2':'按结算时间查询2线记录',
    'bet-sport-game_type':'按投注时间查询体育记录（游戏类型）',
    'bet-sport-pagcor_game_type':'按投注时间查询体育记录（合规分类）',
    'settle-sport-game_type':'按结算时间查询体育记录（游戏类型）',
    'settle-sport-pagcor_game_type':'按结算时间查询体育记录（合规分类）',
    'order-1':'筛选普通投注记录','order-2':'筛选免费旋转记录','order-3':'筛选Jackpot记录',
    'settled':'筛选已结算记录','millisecond-inclusive':'查询已知投注时刻的记录',
    'millisecond-before':'查询已知投注时刻前1毫秒','millisecond-after':'查询已知投注时刻后1毫秒',
    'pagination':'翻页后总记录数与合计保持不变','empty':'无记录时返回空列表',
    'auth-missing':'未登录时拒绝查询','auth-invalid':'登录凭证无效时拒绝查询',
    'page-size-5':'每页选择5条记录','short-10min':'查询包含已知记录的10分钟范围',
    'settle-millisecond':'查询已知结算时刻前后1毫秒',
}

def display_cases(cases):
    rows = []
    for case in cases:
        row = dict(case)
        key = row['用例编号']
        if key.startswith(('bet-', 'game-')):
            prefix, suffix = key.split('-', 1)
            location = '财务管理 · 注单管理' if prefix == 'bet' else '游戏管理 · 投注记录'
            row['用例名称'] = location + '：' + RECORD_NAMES.get(suffix, row['用例名称'])
        elif key.startswith('pending-'):
            row['用例名称'] = {'sport-source':'长周期体育及数据来源核对','historical-node0':'历史线路记录核对','resettlement':'重新结算前后数据核对','roles':'受限账号权限核对','reports':'其他统计报表核对'}.get(key[8:], row['用例名称'])
        rows.append(row)
    return rows
