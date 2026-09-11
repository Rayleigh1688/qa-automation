import json
import unittest
import support
from qa_core.result_language import friendly_row

class FriendlyResults(unittest.TestCase):
    def test_null_is_not_claimed_as_lost_records(self):
        raw=json.dumps([{'path':'body.data.d','op':'type','expected':'array','actual':'NoneType'}])
        row={'用例编号':'example','用例名称':'查询','模块/接口':'示例','执行结果':'FAIL','实际结果/失败点':raw}
        new=friendly_row(row)
        self.assertIn('实际返回空值',new['实际结果/失败点'])
        self.assertIn('不能证明记录丢失',new['实际结果/失败点'])
        self.assertEqual(new['技术断言'],raw)
        self.assertEqual(row['实际结果/失败点'],raw)
        self.assertEqual(new['执行结果'],'FAIL')

    def test_plain_reason_unchanged(self):
        row={'实际结果/失败点':'缺少历史样本'}
        self.assertEqual(friendly_row(row),row)
