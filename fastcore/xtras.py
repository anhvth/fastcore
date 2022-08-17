# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/03_xtras.ipynb.

# %% ../nbs/03_xtras.ipynb 1
from __future__ import annotations

# %% auto 0
__all__ = ['spark_chars', 'walk', 'globtastic', 'maybe_open', 'image_size', 'bunzip', 'loads', 'loads_multi', 'dumps',
           'untar_dir', 'repo_details', 'run', 'open_file', 'save_pickle', 'load_pickle', 'dict2obj', 'obj2dict',
           'repr_dict', 'is_listy', 'mapped', 'IterLen', 'ReindexCollection', 'get_source_link', 'truncstr',
           'sparkline', 'modify_exception', 'round_multiple', 'set_num_threads', 'join_path_file', 'autostart',
           'EventTimer', 'stringfmt_names', 'PartialFormatter', 'partial_format', 'utc2local', 'local2utc', 'trace',
           'modified_env', 'ContextManagers', 'shufflish', 'console_help']

# %% ../nbs/03_xtras.ipynb 3
from .imports import *
from .foundation import *
from .basics import *
from importlib import import_module
from functools import wraps
import string,time
from contextlib import contextmanager,ExitStack
from datetime import datetime, timezone

# %% ../nbs/03_xtras.ipynb 8
def walk(
    path:Path|str, # path to start searching
    symlinks:bool=True, # follow symlinks?
    keep_file:callable=noop, # function that returns True for wanted files
    keep_folder:callable=noop, # function that returns True for folders to enter
    skip_folder:callable=noop, # function that returns True for folders to skip
    func:callable=os.path.join # function to apply to each matched file
): # Generator of `func` applied to matched files
    "Generator version of `os.walk`, using functions to filter files and folders"
    from copy import copy
    for root,dirs,files in os.walk(path, followlinks=symlinks):
        if keep_folder(root,''): yield from (func(root, name) for name in files if keep_file(root,name))
        for name in copy(dirs):
            if skip_folder(root,name): dirs.remove(name)

# %% ../nbs/03_xtras.ipynb 9
def globtastic(
    path:Path|str, # path to start searching
    recursive:bool=True, # search subfolders
    symlinks:bool=True, # follow symlinks?
    file_glob:str=None, # Only include files matching glob
    file_re:str=None, # Only include files matching regex
    folder_re:str=None, # Only enter folders matching regex
    skip_file_glob:str=None, # Skip files matching glob
    skip_file_re:str=None, # Skip files matching regex
    skip_folder_re:str=None, # Skip folders matching regex,
    func:callable=os.path.join # function to apply to each matched file    
)->L: # Paths to matched files
    "A more powerful `glob`, including regex matches, symlink handling, and skip parameters"
    from fnmatch import fnmatch
    path = Path(path)
    if path.is_file(): return L([path])
    if not recursive: skip_folder_re='.'
    file_re,folder_re = compile_re(file_re),compile_re(folder_re)
    skip_file_re,skip_folder_re = compile_re(skip_file_re),compile_re(skip_folder_re)
    def _keep_file(root, name):
        return (not file_glob or fnmatch(name, file_glob)) and (
                not file_re or file_re.search(name)) and (
                not skip_file_glob or not fnmatch(name, skip_file_glob)) and (
                not skip_file_re or not skip_file_re.search(name))
    def _keep_folder(root, name): return not folder_re or folder_re.search(os.path.join(root,name))
    def _skip_folder(root, name): return skip_folder_re and skip_folder_re.search(name)
    return L(walk(path, symlinks=symlinks, keep_file=_keep_file, keep_folder=_keep_folder, skip_folder=_skip_folder, func=func))

# %% ../nbs/03_xtras.ipynb 11
@contextmanager
def maybe_open(f, mode='r', **kwargs):
    "Context manager: open `f` if it is a path (and close on exit)"
    if isinstance(f, (str,os.PathLike)):
        with open(f, mode, **kwargs) as f: yield f
    else: yield f

# %% ../nbs/03_xtras.ipynb 28
def image_size(fn):
    "Tuple of (w,h) for png, gif, or jpg; `None` otherwise"
    import imghdr,struct
    def _jpg_size(f):
        size,ftype = 2,0
        while not 0xc0 <= ftype <= 0xcf:
            f.seek(size, 1)
            byte = f.read(1)
            while ord(byte) == 0xff: byte = f.read(1)
            ftype = ord(byte)
            size = struct.unpack('>H', f.read(2))[0] - 2
        f.seek(1, 1)  # `precision'
        h,w = struct.unpack('>HH', f.read(4))
        return w,h

    def _gif_size(f): return struct.unpack('<HH', head[6:10])

    def _png_size(f):
        assert struct.unpack('>i', head[4:8])[0]==0x0d0a1a0a
        return struct.unpack('>ii', head[16:24])
    d = dict(png=_png_size, gif=_gif_size, jpeg=_jpg_size)
    with maybe_open(fn, 'rb') as f: return d[imghdr.what(f)](f)

# %% ../nbs/03_xtras.ipynb 30
def bunzip(fn):
    "bunzip `fn`, raising exception if output already exists"
    fn = Path(fn)
    assert fn.exists(), f"{fn} doesn't exist"
    out_fn = fn.with_suffix('')
    assert not out_fn.exists(), f"{out_fn} already exists"
    import bz2
    with bz2.BZ2File(fn, 'rb') as src, out_fn.open('wb') as dst:
        for d in iter(lambda: src.read(1024*1024), b''): dst.write(d)

# %% ../nbs/03_xtras.ipynb 32
def loads(s, **kw):
    "Same as `json.loads`, but handles `None`"
    if not s: return {}
    try: import ujson as json
    except ModuleNotFoundError: import json
    return json.loads(s, **kw)

# %% ../nbs/03_xtras.ipynb 33
def loads_multi(s:str):
    "Generator of >=0 decoded json dicts, possibly with non-json ignored text at start and end"
    import json
    _dec = json.JSONDecoder()
    while s.find('{')>=0:
        s = s[s.find('{'):]
        obj,pos = _dec.raw_decode(s)
        if not pos: raise ValueError(f'no JSON object found at {pos}')
        yield obj
        s = s[pos:]

# %% ../nbs/03_xtras.ipynb 35
def dumps(obj, **kw):
    "Same as `json.dumps`, but uses `ujson` if available"
    try: import ujson as json
    except ModuleNotFoundError: import json
    else: kw['escape_forward_slashes']=False
    return json.dumps(obj, **kw)

# %% ../nbs/03_xtras.ipynb 36
def _unpack(fname, out):
    import shutil
    shutil.unpack_archive(str(fname), str(out))
    ls = out.ls()
    return ls[0] if len(ls) == 1 else out

# %% ../nbs/03_xtras.ipynb 37
def untar_dir(fname, dest, rename=False, overwrite=False):
    "untar `file` into `dest`, creating a directory if the root contains more than one item"
    import tempfile,shutil
    with tempfile.TemporaryDirectory() as d:
        out = Path(d)/remove_suffix(Path(fname).stem, '.tar')
        out.mkdir()
        if rename: dest = dest/out.name
        else:
            src = _unpack(fname, out)
            dest = dest/src.name
        if dest.exists():
            if overwrite: shutil.rmtree(dest) if dest.is_dir() else dest.unlink()
            else: return dest
        if rename: src = _unpack(fname, out)
        shutil.move(str(src), dest)
        return dest

# %% ../nbs/03_xtras.ipynb 45
def repo_details(url):
    "Tuple of `owner,name` from ssh or https git repo `url`"
    res = remove_suffix(url.strip(), '.git')
    res = res.split(':')[-1]
    return res.split('/')[-2:]

# %% ../nbs/03_xtras.ipynb 47
def run(cmd, *rest, same_in_win=False, ignore_ex=False, as_bytes=False, stderr=False):
    "Pass `cmd` (splitting with `shlex` if string) to `subprocess.run`; return `stdout`; raise `IOError` if fails"
    # Even the command is same on Windows, we have to add `cmd /c `"
    import subprocess
    if rest:
        if sys.platform == 'win32' and same_in_win:
            cmd = ('cmd', '/c', cmd, *rest)
        else:
            cmd = (cmd,)+rest
    elif isinstance(cmd, str):
        if sys.platform == 'win32' and same_in_win: cmd = 'cmd /c ' + cmd
        import shlex
        cmd = shlex.split(cmd)
    elif isinstance(cmd, list):
        if sys.platform == 'win32' and same_in_win: cmd = ['cmd', '/c'] + cmd
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = res.stdout
    if stderr and res.stderr: stdout += b' ;; ' + res.stderr
    if not as_bytes: stdout = stdout.decode().strip()
    if ignore_ex: return (res.returncode, stdout)
    if res.returncode: raise IOError(stdout)
    return stdout

# %% ../nbs/03_xtras.ipynb 55
def open_file(fn, mode='r', **kwargs):
    "Open a file, with optional compression if gz or bz2 suffix"
    if isinstance(fn, io.IOBase): return fn
    import bz2,gzip,zipfile
    fn = Path(fn)
    if   fn.suffix=='.bz2': return bz2.BZ2File(fn, mode, **kwargs)
    elif fn.suffix=='.gz' : return gzip.GzipFile(fn, mode, **kwargs)
    elif fn.suffix=='.zip': return zipfile.ZipFile(fn, mode, **kwargs)
    else: return open(fn,mode, **kwargs)

# %% ../nbs/03_xtras.ipynb 56
def save_pickle(fn, o):
    "Save a pickle file, to a file name or opened file"
    import pickle
    with open_file(fn, 'wb') as f: pickle.dump(o, f)

# %% ../nbs/03_xtras.ipynb 57
def load_pickle(fn):
    "Load a pickle file from a file name or opened file"
    import pickle
    with open_file(fn, 'rb') as f: return pickle.load(f)

# %% ../nbs/03_xtras.ipynb 60
def dict2obj(d, list_func=L, dict_func=AttrDict):
    "Convert (possibly nested) dicts (or lists of dicts) to `AttrDict`"
    if isinstance(d, (L,list)): return list_func(d).map(dict2obj)
    if not isinstance(d, dict): return d
    return dict_func(**{k:dict2obj(v) for k,v in d.items()})

# %% ../nbs/03_xtras.ipynb 65
def obj2dict(d):
    "Convert (possibly nested) AttrDicts (or lists of AttrDicts) to `dict`"
    if isinstance(d, (L,list)): return list(L(d).map(obj2dict))
    if not isinstance(d, dict): return d
    return dict(**{k:obj2dict(v) for k,v in d.items()})

# %% ../nbs/03_xtras.ipynb 68
def _repr_dict(d, lvl):
    if isinstance(d,dict):
        its = [f"{k}: {_repr_dict(v,lvl+1)}" for k,v in d.items()]
    elif isinstance(d,(list,L)): its = [_repr_dict(o,lvl+1) for o in d]
    else: return str(d)
    return '\n' + '\n'.join([" "*(lvl*2) + "- " + o for o in its])

# %% ../nbs/03_xtras.ipynb 69
def repr_dict(d):
    "Print nested dicts and lists, such as returned by `dict2obj`"
    return _repr_dict(d,0).strip()

# %% ../nbs/03_xtras.ipynb 71
def is_listy(x):
    "`isinstance(x, (tuple,list,L,slice,Generator))`"
    return isinstance(x, (tuple,list,L,slice,Generator))

# %% ../nbs/03_xtras.ipynb 73
def mapped(f, it):
    "map `f` over `it`, unless it's not listy, in which case return `f(it)`"
    return L(it).map(f) if is_listy(it) else f(it)

# %% ../nbs/03_xtras.ipynb 77
@patch
def readlines(self:Path, hint=-1, encoding='utf8'):
    "Read the content of `self`"
    with self.open(encoding=encoding) as f: return f.readlines(hint)

# %% ../nbs/03_xtras.ipynb 78
@patch
def read_json(self:Path, encoding=None, errors=None):
    "Same as `read_text` followed by `loads`"
    return loads(self.read_text(encoding=encoding, errors=errors))

# %% ../nbs/03_xtras.ipynb 79
@patch
def mk_write(self:Path, data, encoding=None, errors=None, mode=511):
    "Make all parent dirs of `self`, and write `data`"
    self.parent.mkdir(exist_ok=True, parents=True, mode=mode)
    self.write_text(data, encoding=encoding, errors=errors)

# %% ../nbs/03_xtras.ipynb 80
@patch
def relpath(self:Path, start=None):
    "Same as `os.path.relpath`, but returns a `Path`, and resolves symlinks"
    return Path(os.path.relpath(self.resolve(), Path(start).resolve()))

# %% ../nbs/03_xtras.ipynb 83
@patch
def ls(self:Path, n_max=None, file_type=None, file_exts=None):
    "Contents of path as a list"
    import mimetypes
    extns=L(file_exts)
    if file_type: extns += L(k for k,v in mimetypes.types_map.items() if v.startswith(file_type+'/'))
    has_extns = len(extns)==0
    res = (o for o in self.iterdir() if has_extns or o.suffix in extns)
    if n_max is not None: res = itertools.islice(res, n_max)
    return L(res)

# %% ../nbs/03_xtras.ipynb 89
@patch
def __repr__(self:Path):
    b = getattr(Path, 'BASE_PATH', None)
    if b:
        try: self = self.relative_to(b)
        except: pass
    return f"Path({self.as_posix()!r})"

# %% ../nbs/03_xtras.ipynb 92
@patch
def delete(self:Path):
    "Delete a file, symlink, or directory tree"
    if not self.exists(): return
    if self.is_dir():
        import shutil
        shutil.rmtree(self)
    else: self.unlink()

# %% ../nbs/03_xtras.ipynb 94
class IterLen:
    "Base class to add iteration to anything supporting `__len__` and `__getitem__`"
    def __iter__(self): return (self[i] for i in range_of(self))

# %% ../nbs/03_xtras.ipynb 95
@docs
class ReindexCollection(GetAttr, IterLen):
    "Reindexes collection `coll` with indices `idxs` and optional LRU cache of size `cache`"
    _default='coll'
    def __init__(self, coll, idxs=None, cache=None, tfm=noop):
        if idxs is None: idxs = L.range(coll)
        store_attr()
        if cache is not None: self._get = functools.lru_cache(maxsize=cache)(self._get)

    def _get(self, i): return self.tfm(self.coll[i])
    def __getitem__(self, i): return self._get(self.idxs[i])
    def __len__(self): return len(self.coll)
    def reindex(self, idxs): self.idxs = idxs
    def shuffle(self):
        import random
        random.shuffle(self.idxs)
    def cache_clear(self): self._get.cache_clear()
    def __getstate__(self): return {'coll': self.coll, 'idxs': self.idxs, 'cache': self.cache, 'tfm': self.tfm}
    def __setstate__(self, s): self.coll,self.idxs,self.cache,self.tfm = s['coll'],s['idxs'],s['cache'],s['tfm']

    _docs = dict(reindex="Replace `self.idxs` with idxs",
                shuffle="Randomly shuffle indices",
                cache_clear="Clear LRU cache")

# %% ../nbs/03_xtras.ipynb 114
def _is_type_dispatch(x): return type(x).__name__ == "TypeDispatch"
def _unwrapped_type_dispatch_func(x): return x.first() if _is_type_dispatch(x) else x

def _is_property(x): return type(x)==property
def _has_property_getter(x): return _is_property(x) and hasattr(x, 'fget') and hasattr(x.fget, 'func')
def _property_getter(x): return x.fget.func if _has_property_getter(x) else x

def _unwrapped_func(x):
    x = _unwrapped_type_dispatch_func(x)
    x = _property_getter(x)
    return x


def get_source_link(func):
    "Return link to `func` in source code"
    import inspect
    func = _unwrapped_func(func)
    try: line = inspect.getsourcelines(func)[1]
    except Exception: return ''
    mod = inspect.getmodule(func)
    module = mod.__name__.replace('.', '/') + '.py'
    try:
        nbdev_mod = import_module(mod.__package__.split('.')[0] + '._nbdev')
        return f"{nbdev_mod.git_url}{module}#L{line}"
    except: return f"{module}#L{line}"

# %% ../nbs/03_xtras.ipynb 117
def truncstr(s:str, maxlen:int, suf:str='…', space='')->str:
    "Truncate `s` to length `maxlen`, adding suffix `suf` if truncated"
    return s[:maxlen-len(suf)]+suf if len(s)+len(space)>maxlen else s+space

# %% ../nbs/03_xtras.ipynb 119
spark_chars = '▁▂▃▅▆▇'

# %% ../nbs/03_xtras.ipynb 120
def _ceil(x, lim=None): return x if (not lim or x <= lim) else lim

def _sparkchar(x, mn, mx, incr, empty_zero):
    if x is None or (empty_zero and not x): return ' '
    if incr == 0: return spark_chars[0]
    res = int((_ceil(x,mx)-mn)/incr-0.5)
    return spark_chars[res]

# %% ../nbs/03_xtras.ipynb 121
def sparkline(data, mn=None, mx=None, empty_zero=False):
    "Sparkline for `data`, with `None`s (and zero, if `empty_zero`) shown as empty column"
    valid = [o for o in data if o is not None]
    if not valid: return ' '
    mn,mx,n = ifnone(mn,min(valid)),ifnone(mx,max(valid)),len(spark_chars)
    res = [_sparkchar(x=o, mn=mn, mx=mx, incr=(mx-mn)/n, empty_zero=empty_zero) for o in data]
    return ''.join(res)

# %% ../nbs/03_xtras.ipynb 125
def modify_exception(
    e:Exception, # An exception
    msg:str=None, # A custom message
    replace:bool=False, # Whether to replace e.args with [msg]
) -> Exception:
    "Modifies `e` with a custom message attached"
    e.args = [f'{e.args[0]} {msg}'] if not replace and len(e.args) > 0 else [msg]
    return e

# %% ../nbs/03_xtras.ipynb 127
def round_multiple(x, mult, round_down=False):
    "Round `x` to nearest multiple of `mult`"
    def _f(x_): return (int if round_down else round)(x_/mult)*mult
    res = L(x).map(_f)
    return res if is_listy(x) else res[0]

# %% ../nbs/03_xtras.ipynb 129
def set_num_threads(nt):
    "Get numpy (and others) to use `nt` threads"
    try: import mkl; mkl.set_num_threads(nt)
    except: pass
    try: import torch; torch.set_num_threads(nt)
    except: pass
    os.environ['IPC_ENABLE']='1'
    for o in ['OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:
        os.environ[o] = str(nt)

# %% ../nbs/03_xtras.ipynb 131
def join_path_file(file, path, ext=''):
    "Return `path/file` if file is a string or a `Path`, file otherwise"
    if not isinstance(file, (str, Path)): return file
    path.mkdir(parents=True, exist_ok=True)
    return path/f'{file}{ext}'

# %% ../nbs/03_xtras.ipynb 134
def autostart(g):
    "Decorator that automatically starts a generator"
    @functools.wraps(g)
    def f():
        r = g()
        next(r)
        return r
    return f

# %% ../nbs/03_xtras.ipynb 135
class EventTimer:
    "An event timer with history of `store` items of time `span`"

    def __init__(self, store=5, span=60):
        import collections
        self.hist,self.span,self.last = collections.deque(maxlen=store),span,time.perf_counter()
        self._reset()

    def _reset(self): self.start,self.events = self.last,0

    def add(self, n=1):
        "Record `n` events"
        if self.duration>self.span:
            self.hist.append(self.freq)
            self._reset()
        self.events +=n
        self.last = time.perf_counter()

    @property
    def duration(self): return time.perf_counter()-self.start
    @property
    def freq(self): return self.events/self.duration

# %% ../nbs/03_xtras.ipynb 139
_fmt = string.Formatter()

# %% ../nbs/03_xtras.ipynb 140
def stringfmt_names(s:str)->list:
    "Unique brace-delimited names in `s`"
    return uniqueify(o[1] for o in _fmt.parse(s) if o[1])

# %% ../nbs/03_xtras.ipynb 142
class PartialFormatter(string.Formatter):
    "A `string.Formatter` that doesn't error on missing fields, and tracks missing fields and unused args"
    def __init__(self):
        self.missing = set()
        super().__init__()

    def get_field(self, nm, args, kwargs):
        try: return super().get_field(nm, args, kwargs)
        except KeyError:
            self.missing.add(nm)
            return '{'+nm+'}',nm

    def check_unused_args(self, used, args, kwargs):
        self.xtra = filter_keys(kwargs, lambda o: o not in used)

# %% ../nbs/03_xtras.ipynb 144
def partial_format(s:str, **kwargs):
    "string format `s`, ignoring missing field errors, returning missing and extra fields"
    fmt = PartialFormatter()
    res = fmt.format(s, **kwargs)
    return res,list(fmt.missing),fmt.xtra

# %% ../nbs/03_xtras.ipynb 147
def utc2local(dt:datetime)->datetime:
    "Convert `dt` from UTC to local time"
    return dt.replace(tzinfo=timezone.utc).astimezone(tz=None)

# %% ../nbs/03_xtras.ipynb 149
def local2utc(dt:datetime)->datetime:
    "Convert `dt` from local to UTC time"
    return dt.replace(tzinfo=None).astimezone(tz=timezone.utc)

# %% ../nbs/03_xtras.ipynb 151
def trace(f):
    "Add `set_trace` to an existing function `f`"
    from pdb import set_trace
    if getattr(f, '_traced', False): return f
    def _inner(*args,**kwargs):
        set_trace()
        return f(*args,**kwargs)
    _inner._traced = True
    return _inner

# %% ../nbs/03_xtras.ipynb 153
@contextmanager
def modified_env(*delete, **replace):
    "Context manager temporarily modifying `os.environ` by deleting `delete` and replacing `replace`"
    prev = dict(os.environ)
    try:
        os.environ.update(replace)
        for k in delete: os.environ.pop(k, None)
        yield
    finally:
        os.environ.clear()
        os.environ.update(prev)

# %% ../nbs/03_xtras.ipynb 155
class ContextManagers(GetAttr):
    "Wrapper for `contextlib.ExitStack` which enters a collection of context managers"
    def __init__(self, mgrs): self.default,self.stack = L(mgrs),ExitStack()
    def __enter__(self): self.default.map(self.stack.enter_context)
    def __exit__(self, *args, **kwargs): self.stack.__exit__(*args, **kwargs)

# %% ../nbs/03_xtras.ipynb 157
def shufflish(x, pct=0.04):
    "Randomly relocate items of `x` up to `pct` of `len(x)` from their starting location"
    n = len(x)
    import random
    return L(x[i] for i in sorted(range_of(x), key=lambda o: o+n*(1+random.random()*pct)))

# %% ../nbs/03_xtras.ipynb 158
def console_help(
    libname:str):  # name of library for console script listing
    "Show help for all console scripts from `libname`"
    from pkg_resources import iter_entry_points as ep
    for e in ep('console_scripts'): 
        if e.module_name.startswith(libname+'.'): 
            nm = f'\033[1m\033[94m{e.name}\033[0m'
            print(f'{nm:45}{e.load().__doc__}')
