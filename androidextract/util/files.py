import os

def files(path):
    for file in os.listdir(path):
        if os.path.isfile(os.path.join(path, file)):
            yield os.path.join(path, file)

def directories(path):
    for file in os.listdir(path):
        if os.path.isdir(os.path.join(path, file)):
            yield os.path.join(path, file)

def mkdir(path):
    """Same as os.mkdir but ignores errors due to existing directories"""
    try:
        os.mkdir(path)
    except FileExistsError:
        pass

def mkdir_recursive(path):
    total_path = ""
    for component in os.path.normpath(path).split(os.sep):
        total_path = os.path.join(total_path, component)
        mkdir(total_path)

def chown_parents(path, uid, gid):
    if os.path.isabs(path):
        raise ValueError("Path must not be absolute (this is always an error)")

    total_path = ""
    for component in os.path.normpath(path).split(os.sep):
        total_path = os.path.join(total_path, component)
        os.chown(total_path, uid, gid)

def chown_recursive(path, uid, gid):
    includeroot = True
    for root, dirs, files in os.walk(path, followlinks=False):
        if includeroot:
            objects = ["."] + dirs + files
            includeroot = False
        else:
            objects = dirs + files

        for obj in objects:
            path = os.path.join(root, obj)
            path = os.path.normpath(path)
            os.chown(path, uid, gid)

def get_all_files(toplevel_path, depth=None, relative=False):
    def handle_error(exp):
        if isinstance(exp, OSError):
            if exp.errno == errno.EACCES:
                log.error("Unable to access file during walk. Make sure you are root!")
                sys.exit(1)

        raise

    toplevel_path = os.path.normpath(toplevel_path)

    parent_components = len(toplevel_path.split(os.sep))
    current_depth = 0
    found_files = []

    for root, dirs, files in os.walk(toplevel_path, topdown=bool(depth), onerror=handle_error, followlinks=False):
        objects = dirs + files

        if depth and current_depth >= depth:
            break

        for obj in objects:
            path = os.path.join(root, obj)
            path = os.path.normpath(path)

            # strip off the parent directory
            if relative:
                path = os.path.join(*path.split(os.sep)[parent_components:])

            found_files += [{"name" : path}]

        current_depth += 1

    return found_files

