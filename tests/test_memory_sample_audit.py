import contextlib,importlib.util,io,json,math,pathlib,tempfile,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]/"tools"
spec=importlib.util.spec_from_file_location("target_mem_audit",ROOT/"memory_sample_audit.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
def reject_nonfinite(value):
 raise ValueError("Non-finite JSON constant: "+value)

class RiskTests(unittest.TestCase):
 def output(self,sample):
  with tempfile.TemporaryDirectory() as tmp, patch.object(mod,"os_mem",return_value=sample),patch.object(mod,"pagefile",return_value={}),patch.object(mod,"procs",return_value=[]),patch("sys.argv",["mem_audit.py","--out-dir",tmp]),contextlib.redirect_stdout(io.StringIO()):
   mod.main()
   return json.loads(next(pathlib.Path(tmp).glob("*.json")).read_text(encoding="utf-8"),parse_constant=reject_nonfinite),next(pathlib.Path(tmp).glob("*.md")).read_text(encoding="utf-8")
 def test_missing_or_invalid_measurement_never_reports_safe(self):
  cases=[{},{"total_mb":None,"free_mb":None},{"total_mb":0,"free_mb":0},{"total_mb":-1,"free_mb":0},{"total_mb":100,"free_mb":-1},{"total_mb":100,"free_mb":101},{"total_mb":float("nan"),"free_mb":1},{"total_mb":100,"free_mb":float("inf")},{"total_mb":True,"free_mb":0},{"total_mb":"100","free_mb":5}]
  for sample in cases:
   with self.subTest(sample=sample):
    data,md=self.output(sample);risk=data["R_mem"]
    self.assertEqual(risk["state"],"未实测")
    for key in ("R_mem_mb","mem_available_mb","total_mb","M_floor_mb","breached","sampled_at_utc"):self.assertIsNone(risk[key],key)
    self.assertFalse(risk["measurement_valid"])
    self.assertIn("未评估",md)
    self.assertNotIn("高于安全下限",md)
 def test_measured_zero_is_low_not_missing(self):
  data,_=self.output({"total_mb":10000,"free_mb":0})
  self.assertEqual(data["R_mem"]["R_mem_mb"],800)
  self.assertEqual(data["R_mem"]["state"],"低于安全下限")
 def test_valid_boundary_and_above(self):
  for free in (800,801):
   with self.subTest(free=free):
    data,_=self.output({"total_mb":10000,"free_mb":free})
    self.assertEqual(data["R_mem"]["R_mem_mb"],0)
    self.assertEqual(data["R_mem"]["state"],"高于安全下限")

class CollectionFailureTests(unittest.TestCase):
 def test_failed_collectors_are_reported_without_false_health(self):
  import subprocess
  cases=[subprocess.TimeoutExpired("powershell",1), FileNotFoundError("powershell unavailable"), subprocess.CompletedProcess(["powershell"],1,stdout="102400|51200|204800|102400",stderr="failed")]
  for failure in cases:
   with self.subTest(failure=type(failure).__name__):
    opts={"side_effect":failure} if isinstance(failure,Exception) else {"return_value":failure}
    with tempfile.TemporaryDirectory() as tmp,patch.object(mod.subprocess,"run",**opts),patch("sys.argv",["mem_audit.py","--out-dir",tmp]),contextlib.redirect_stdout(io.StringIO()):
     mod.main()
     data=json.loads(next(pathlib.Path(tmp).glob("*.json")).read_text(encoding="utf-8"),parse_constant=reject_nonfinite)
     md=next(pathlib.Path(tmp).glob("*.md")).read_text(encoding="utf-8")
     self.assertEqual(data["R_mem"]["state"],"未实测")
     for key in ("memory","pagefile","processes"):
      self.assertEqual(data["sampling"][key]["status"],"failed")
     self.assertIn("进程采样未完成",md)
     self.assertNotIn("| 无候选 |",md)


class RawSampleValidationTests(unittest.TestCase):
 def test_raw_kib_range_before_rounding(self):
  for raw in ("10240000|-1|20480000|10240000","10240000|10240001|20480000|10240000","0|0|20480000|10240000"):
   with self.subTest(raw=raw),patch.object(mod,"ps",return_value=raw):
    self.assertEqual(mod.os_mem(),{})
 def test_valid_raw_zero_remains_measured(self):
  with patch.object(mod,"ps",return_value="10240000|0|20480000|10240000"):
   self.assertEqual(mod.memory_risk(mod.os_mem(),"test")["state"],"低于安全下限")

if __name__=="__main__":unittest.main()
