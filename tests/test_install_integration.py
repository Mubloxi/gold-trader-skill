import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import subprocess
import sys
import tomllib

ROOT=Path(__file__).resolve().parent.parent

class Installation(TestCase):
    def test_both_project_installers_and_cli(self):
        with TemporaryDirectory() as t:
            for host,agentdir,glob,skill in (
                ("claude",".claude/agents","*.md",".claude/skills"),
                ("codex",".codex/agents","*.toml",".agents/skills")):
                dest=Path(t)/host
                cmd=[sys.executable,str(ROOT/"scripts/install.py"),host,"--target",str(dest)]
                subprocess.run(cmd,check=True,capture_output=True)
                subprocess.run(cmd,check=True,capture_output=True)
                actual=list((dest/agentdir).glob(glob))
                self.assertEqual(len(actual),15)
                self.assertIn("name: xauusd-research",
                        (dest/skill/"xauusd-research/SKILL.md").read_text(encoding="utf-8"))
                for a in actual:
                    if host=="codex":
                        self.assertEqual(tomllib.loads(a.read_text(encoding="utf-8"))["name"],a.stem)
                    else:
                        self.assertIn("name: "+a.stem,a.read_text(encoding="utf-8"))
                run=subprocess.run([sys.executable,"-m","gold_desk","prepare","--session","offline"],cwd=dest,
                                   text=True,capture_output=True,check=True)
                self.assertEqual(json.loads(run.stdout)["method"],"offline-no-agents")
                p=dest/"README.md"
                p.write_text("do not overwrite",encoding="utf-8")
                self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,2)
                self.assertEqual(p.read_text(encoding="utf-8"),"do not overwrite")

    def test_manifests_and_windows_wrapper(self):
        plugin=json.loads((ROOT/".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertTrue((ROOT/plugin["skills"]/"xauusd-research/SKILL.md").exists())
        self.assertTrue(all((ROOT/path).is_file() for path in plugin["agents"]))
        mp=json.loads((ROOT/".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(mp["plugins"][0]["name"],plugin["name"])
        win=(ROOT/"install.ps1").read_text(encoding="utf-8")
        self.assertIn("scripts/install.py",win)
        self.assertIn("py -3",win)

    def test_missing_csv_produces_insufficient_report(self):
        with TemporaryDirectory() as t:
            out=Path(t)/"research"
            subprocess.run([sys.executable,"-m","gold_desk","prepare","--csv",str(out/"missing.csv"),
                            "--session",str(out)],cwd=ROOT,capture_output=True,check=True)
            data=json.loads((out/"report.json").read_text(encoding="utf-8"))
            self.assertIn("invalid",data["gaps_and_errors"][0])
            self.assertEqual(data["research_conclusion"],"insufficient evidence")

    def test_demo_subprocess_writes_reports_with_virtual_funds(self):
        with TemporaryDirectory() as t:
            d=Path(t)/"run"
            subprocess.run([sys.executable,str(ROOT/"scripts/demo.py"),"--out",str(d)],
                           cwd=ROOT,check=True,capture_output=True)
            summary=json.loads((d/"demo-summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["events"],["hypothesis","risk","open","close"])
            self.assertEqual(summary["virtual_account"]["initial"],250.)
            self.assertEqual(summary["research_execution"],"offline-no-agents")
            self.assertIn("SYNTHETIC",(d/"research/report.md").read_text(encoding="utf-8"))
            self.assertTrue((d/"virtual.sqlite").is_file())
