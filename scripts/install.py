"""Copy a project-scoped, reviewable installation. No package installs or credential access."""
import argparse
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parent.parent

def install(platform,target):
    tree=ROOT/"platforms"/platform
    files={p.relative_to(tree):p for p in tree.rglob("*") if p.is_file()}
    for group,pattern in (("gold_desk","*.py"),("config","*.json"),("docs","*.md")):
        for p in (ROOT/group).glob(pattern):
            files[p.relative_to(ROOT)]=p
    for n in ("LICENSE","NOTICE","README.md"):
        files[Path(n)]=ROOT/n
    resolved_target=target.resolve()
    for relative,src in files.items():
        out=target/relative
        if not out.resolve().is_relative_to(resolved_target) or out.is_symlink():
            raise ValueError(f"unsafe install destination: {relative}")
        if out.exists() and (not out.is_file() or src.read_bytes()!=out.read_bytes()):
            raise ValueError(f"refusing to overwrite {out}")
    for relative,src in files.items():
        out=target/relative
        out.parent.mkdir(parents=True,exist_ok=True)
        if not out.exists():
            shutil.copyfile(src,out)
    return len(files)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("platform",choices=["claude","codex"])
    p.add_argument("--target",type=Path,required=True)
    a=p.parse_args()
    try:
        count=install(a.platform,a.target)
    except (OSError,ValueError) as e:
        p.exit(2,"Install: "+str(e)+"\n")
    print(f"Verified or installed {count} project files in {a.target.resolve()}")

if __name__=="__main__":
    main()
