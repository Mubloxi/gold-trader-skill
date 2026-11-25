"""Build a deterministic source ZIP; never include caches, credentials, or account data."""
from argparse import ArgumentParser
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import stat

ROOT=Path(__file__).resolve().parent.parent
ALLOWED={"gold_desk","tests","platforms","docs","scripts","config","examples",".claude-plugin"}
TOP={".env.example",".gitignore","LICENSE","NOTICE","README.md","install.sh","install.ps1"}
SKIP={"__pycache__",".gold-cache",".pytest_cache"}
def package(out):
    out.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(out,"w") as z:
        for p in sorted(ROOT.rglob("*")):
            rel=p.relative_to(ROOT)
            if (not p.is_file() or p.is_symlink() or SKIP.intersection(rel.parts) or
                p.suffix in {".sqlite",".pyc"} or p.name==".env"):
                continue
            if not ((len(rel.parts)==1 and p.name in TOP) or rel.parts[0] in ALLOWED):
                continue
            entry=ZipInfo(f"{ROOT.name}/{rel.as_posix()}",date_time=(2026,11,25,0,0,0))
            entry.create_system=3
            entry.external_attr=(stat.S_IFREG|(0o755 if p.name=="install.sh" else 0o644))<<16
            z.writestr(entry,p.read_bytes(),compress_type=ZIP_DEFLATED,compresslevel=9)
    return out

if __name__=="__main__":
    p=ArgumentParser(description=__doc__)
    p.add_argument("out",type=Path)
    print(package(p.parse_args().out))
