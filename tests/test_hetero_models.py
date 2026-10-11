"""OPL-HETERO-TEST-20261009-01 / codex-review-20261005.
Offline route/security behavior, separate from provider authentication receipts.
"""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.error
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import hetero_models as h

class RouteTests(unittest.TestCase):
    def call302(self, model, reviewed=()):
        return h.chat(model, 'SYNTHETIC PING', base=h.PLATFORMS['302.ai']['base'],
                      key_env='AI302_KEY', max_tokens=16, verified_foreign_models=reviewed)

    def test_unapproved_destination_or_wrong_credential_never_reads_key(self):
        for base, key in [('https://unapproved.invalid/v1','AI302_KEY'),
                          ('https://api.302.ai/v1','AI302_KEY'),
                          ('https://api.302ai.cn/v1','SILICONFLOW_KEY')]:
            with self.subTest(base=base), patch.object(h,'_key') as keyread:
                result=h.chat('gpt-fixture','SYNTHETIC',base=base,key_env=key)
                self.assertEqual(result['error'],'unapproved_endpoint_or_credential_binding')
                keyread.assert_not_called()

    def test_302_domestic_unknown_and_unreviewed_models_fail_before_request(self):
        for model,reviewed in [('Qwen/model',{'Qwen/model'}),('deepseek-v3',{'deepseek-v3'}),
                ('gpt-qwen-proxy',{'gpt-qwen-proxy'}),('opaque-model',{'opaque-model'}),
                ('gpt-fixture',()),('gpt-fixture','gpt-fixture')]:
            with self.subTest(model=model), patch.object(h,'_request') as request:
                self.assertEqual(self.call302(model,reviewed)['error'],'302_foreign_model_not_verified')
                request.assert_not_called()

    def test_reviewed_302_model_uses_exact_endpoint_and_bounded_payload(self):
        response={'model':'gpt-fixture','choices':[{'message':{'content':'PING_OK'}}],
                  'usage':{'total_tokens':10}}
        with patch.object(h,'_request',return_value=response) as request:
            self.assertEqual(self.call302('gpt-fixture',{'gpt-fixture'})['tokens'],10)
            provider,path,payload=request.call_args.args
            self.assertEqual((provider,path,payload['max_tokens']),('302.ai','/chat/completions',16))
            self.assertEqual(payload['messages'][0]['content'],'SYNTHETIC PING')

    def test_invalid_limits_and_response_shapes_cannot_report_success(self):
        for limit in [True,0,4097,1.5]:
            with self.subTest(limit=limit),patch.object(h,'_request') as request:
                self.assertEqual(h.chat('model','SYNTHETIC',max_tokens=limit)['error'],'invalid_output_limit')
                request.assert_not_called()
        for value in [{}, {'choices':[]}, {'choices':[{'message':{'content':None}}]},
                      {'choices':[{'message':{'content':'OK'}}],'usage':{'total_tokens':-1}}]:
            with patch.object(h,'_request',return_value=value):
                self.assertEqual(h.chat('model','SYNTHETIC')['error'],'response_shape_unverified')

    def test_302_response_identity_mismatch_discards_content(self):
        for response_model in [None,'Qwen/model','gpt-unreviewed']:
            with self.subTest(model=response_model),patch.object(h,'_request',return_value={
                'model':response_model,'choices':[{'message':{'content':'DO_NOT_RETURN_CONTENT'}}]}):
                result=self.call302('gpt-fixture',{'gpt-fixture'})
                self.assertEqual(result['error'],'302_response_identity_unverified')
                self.assertNotIn('DO_NOT_RETURN',json.dumps(result))

    def test_remote_error_text_is_not_returned(self):
        opener=Mock();opener.open.side_effect=RuntimeError('DO_NOT_RETURN_SECRET_FIXTURE')
        with patch.object(h,'_key',return_value='fixture-credential'),patch.object(h.urllib.request,'build_opener',return_value=opener):
            result=h.catalog('302.ai')
        self.assertEqual(result['error'],'request_failed')
        self.assertNotIn('DO_NOT_RETURN',json.dumps(result))
        self.assertNotIn('fixture-credential',json.dumps(result))

    def test_http_rejection_and_redirect_are_safe(self):
        self.assertIsNone(h.NoRedirect().redirect_request(None,None,302,'',{},'https://unapproved.invalid'))
        opener=Mock();opener.open.side_effect=urllib.error.HTTPError('https://api.302ai.cn/v1/models',302,'SECRET_FIXTURE',{},io.BytesIO(b'SECRET_FIXTURE'))
        with patch.object(h,'_key',return_value='fixture-credential'),patch.object(h.urllib.request,'build_opener',return_value=opener):
            result=h.catalog('302.ai')
        self.assertEqual(result['http_status'],302)
        self.assertNotIn('SECRET_FIXTURE',json.dumps(result))

    def test_catalog_filters_ids_and_keeps_authentication_separate_from_inference(self):
        with patch.object(h,'_request',return_value={'data':[{'id':'gpt-fixture'}, {'id':'bad@example.invalid'}, {'id':'sk-fixture-long'}, {'id':'gpt-fixture'},None]}):
            result=h.catalog('302.ai')
        self.assertEqual(result['models'],['gpt-fixture'])
        self.assertTrue(result['authenticated_catalog_read'])
        self.assertFalse(result['inference_verified'])

    def test_key_file_quotes_and_presence_do_not_assert_authentication(self):
        # A real isolated file works on a runner with no managed key file.
        # Patching isfile did not cover exists and concealed that dependency locally.
        with tempfile.TemporaryDirectory() as directory:
            fixture=Path(directory)/'fixture.env'
            fixture.write_text('AI302_KEY="fixture-credential"\n# comment\n',encoding='utf-8-sig')
            with patch.object(h,'KEY_FILE',str(fixture)):
                values=h._load_keys()
                fixture.unlink()
                self.assertEqual(h._load_keys(),{})
        self.assertEqual(values['AI302_KEY'],'fixture-credential')
        with patch.object(h,'_load_keys',return_value=values):
            result=h.status()
        self.assertTrue(result['302.ai']['has_key'])
        self.assertFalse(result['302.ai']['authentication_verified'])

if __name__=='__main__':unittest.main()
