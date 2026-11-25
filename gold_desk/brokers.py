"""Local broker profiles. Discover installed terminal paths without launching them."""
from pathlib import Path
import os
import re

from .core import read_json, write_json
from .mt5_feed import MT5_FRAMES

PRESETS = {
    "pepperstone": ("Pepperstone", ("pepperstone",)),
    "vanga": ("Vanga (user-configured MT5)", ("vanga",)),
    "generic": ("Other MT5 broker", ()),
}
EXE_NAMES = {"terminal64.exe", "terminal.exe", "metatrader64.exe", "metatrader.exe"}
PROFILE_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")
SYMBOL = re.compile(r"[A-Za-z0-9._+/#-]{1,48}")


def profile_path():
    base = os.environ.get("LOCALAPPDATA")
    return (Path(base) if base else Path.home()/".config")/"gold-trader-skill"/"brokers.json"


def _valid_name(name):
    if not isinstance(name,str) or not PROFILE_NAME.fullmatch(name):
        raise ValueError("profile names must be 1–32 lowercase letters, numbers or hyphens")
    return name


def _validate(profile):
    if not isinstance(profile,dict) or set(profile)!={"preset","terminal","symbol","frame"}:
        raise ValueError("invalid broker profile fields")
    if (profile["preset"] not in PRESETS or profile["frame"] not in MT5_FRAMES or
            not isinstance(profile["symbol"],str) or not SYMBOL.fullmatch(profile["symbol"])):
        raise ValueError("invalid broker preset, symbol or timeframe")
    raw=profile["terminal"]
    if not isinstance(raw,str):
        raise ValueError("broker profile requires a terminal path")
    terminal=Path(raw)
    if not terminal.is_absolute() or terminal.name.lower() not in EXE_NAMES:
        raise ValueError("broker profile terminal must be an absolute path to an MT5 executable")
    return profile


class BrokerProfiles:
    def __init__(self,path=None):
        self.path=Path(path) if path is not None else profile_path()

    def load(self):
        if not self.path.exists():
            return {"version":1,"active":None,"profiles":{}}
        data=read_json(self.path)
        if (not isinstance(data,dict) or set(data)!={"version","active","profiles"} or
                data["version"]!=1 or not isinstance(data["profiles"],dict)):
            raise ValueError("invalid broker profile file")
        for name,profile in data["profiles"].items():
            _valid_name(name)
            _validate(profile)
        if data["active"] is not None and data["active"] not in data["profiles"]:
            raise ValueError("active broker profile is missing")
        return data

    def active(self):
        return self.load()["active"]

    def get(self,name=None):
        data=self.load()
        name=name or data["active"]
        if name is None:
            raise ValueError("no broker configured; run broker setup first")
        if name not in data["profiles"]:
            raise ValueError(f"broker profile '{name}' is not configured; run broker list")
        return name,data["profiles"][name]

    def save(self,name,profile):
        data=self.load()
        data["profiles"][_valid_name(name)]=_validate(profile)
        data["active"]=name
        write_json(self.path,data)

    def use(self,name):
        data=self.load()
        if name not in data["profiles"]:
            raise ValueError(f"broker profile '{name}' is not configured")
        data["active"]=name
        write_json(self.path,data)


def _roots():
    for key in ("ProgramFiles","ProgramFiles(x86)","ProgramW6432"):
        if value:=os.getenv(key):
            yield Path(value)
    if local:=os.getenv("LOCALAPPDATA"):
        yield Path(local)/"Programs"


def discover(preset, *, roots=None):
    """Only check common installation roots and their immediate broker folders."""
    _,tokens=PRESETS[preset]
    out=set()
    roots=list(_roots()) if roots is None else roots
    for root in roots:
        try:
            for folder in root.iterdir():
                if not folder.is_dir() or (tokens and not any(t in folder.name.lower() for t in tokens)):
                    continue
                for name in sorted(EXE_NAMES):
                    path=folder/name
                    if path.is_file():
                        out.add(str(path.resolve()))
        except OSError:
            continue
    return sorted(out,key=str.casefold)


def setup(args):
    store=BrokerProfiles()
    preset=args.preset
    name=args.name or preset
    path=args.terminal
    if path is None:
        candidates=discover(preset)
        if len(candidates)!=1:
            raise ValueError("no unique MT5 terminal found; run broker paths "+preset+
                             " or pass --terminal with its exact executable path")
        path=Path(candidates[0])
    path=path.expanduser().resolve()
    if not path.is_file() or path.name.lower() not in EXE_NAMES:
        raise ValueError("supply an existing MT5 executable, usually terminal64.exe")
    profile={"preset":preset,"terminal":str(path),"symbol":args.symbol,"frame":args.frame}
    store.save(name,profile)
    return {"saved":name,"profile_file":str(store.path),"profile":profile,"connection_checked":False}


def broker_command(args):
    store=BrokerProfiles()
    if args.action=="setup":
        return setup(args)
    if args.action=="paths":
        return {"preset":args.preset,"candidates":discover(args.preset)}
    if args.action=="use":
        store.use(args.name)
        return {"active":args.name}
    if args.action=="show":
        name,data=store.get(args.name)
        return {"profile":name,"settings":data,"profile_file":str(store.path)}
    return {"available_presets":{k:v[0] for k,v in PRESETS.items()},
            "saved_profiles":sorted(store.load()["profiles"]),"active":store.active()}
