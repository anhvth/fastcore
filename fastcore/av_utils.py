from functools import wraps
import os
import xxhash
import pickle
import json
from loguru import logger
import inspect
import os.path as osp

AVCV_CACHE_DIR = osp.join(osp.expanduser('~'), '.cache/avcv')
ICACHE = dict()

def mkdir_or_exist(dir_name):
    return os.makedirs(dir_name, exist_ok=True)

def dump_json_or_pickle(obj, fname):
    """
        Dump an object to a file, support both json and pickle
    """
    if fname.endswith('.json'):
        with open(fname, 'w') as f:
            json.dump(obj, f)
    else:
        with open(fname, 'wb') as f:
            pickle.dump(obj, f)
            
def load_json_or_pickle(fname):
    """
        Load an object from a file, support both json and pickle
    """
    if fname.endswith('.json'):
        with open(fname, 'r') as f:
            return json.load(f)
    else:
        with open(fname, 'rb') as f:
            return pickle.load(f)
        
def identify(x):
    '''Return an hex digest of the input'''
    return xxhash.xxh64(pickle.dumps(x), seed=0).hexdigest()


def memoize(func):

    '''Cache result of function call on disk
    Support multiple positional and keyword arguments'''
    @wraps(func)
    def memoized_func(*args, **kwargs):
        try:
            if 'cache_key' in kwargs:
                cache_key = kwargs['cache_key']
                
                func_id = identify((inspect.getsource(func)))+'_cache_key_'+str(kwargs['cache_key'])
            else:
                func_id = identify((inspect.getsource(func), args, kwargs))
            cache_path = os.path.join(AVCV_CACHE_DIR, 'funcs', func.__name__+'/'+func_id)
            mkdir_or_exist(os.path.dirname(cache_path))

            if (os.path.exists(cache_path) and
                    not func.__name__ in os.environ and
                    not 'BUST_CACHE' in os.environ):
                result = pickle.load(open(cache_path, 'rb'))
            else:
                result = func(*args, **kwargs)
                pickle.dump(result, open(cache_path, 'wb'))
            return result
        except (KeyError, AttributeError, TypeError, Exception) as e:
            logger.warning(f'Exception: {e}, use default function call')
            return func(*args, **kwargs)
    return memoized_func

def imemoize(func):
    """
        Memoize a function into memory, the function recaculate only 
        change when its belonging arguments change
    """
    @wraps(func)
    def _f(*args, **kwargs):
        ident_name = identify((inspect.getsource(func), args, kwargs))
        try:
            result = ICACHE[ident_name]
        except:
            result = func(*args, **kwargs)
            ICACHE[ident_name] = result
        return result
    return _f
