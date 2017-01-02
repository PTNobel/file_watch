import time
import os
import sys
from typing import List, Tuple, Dict, Any, Callable, NewType

ProcessedArgs = Dict[str, Any]
Recipe = NewType("Recipe", Dict[str, Any])
MainForFileMethod = Callable[[ProcessedArgs], None]
FilePair = Tuple[MainForFileMethod, ProcessedArgs]


class FileWatch:
    _failed_reads = 0

    def __init__(self, file_name: str) -> None:
        self._file_name = file_name
        self._last_content = self._read_file()

    def _read_file(self) -> List[str]:
        try:
            fd = open(self._file_name)
        except FileNotFoundError as e:
            self._failed_reads += 1
            if self._failed_reads <= 5:
                time.sleep(.3)
                return self._read_file()
            else:
                raise e
        filecontents = fd.readlines()
        fd.close()
        return filecontents

    def hasItChanged(self) -> bool:
        self._failed_reads = 0
        _new_content = self._read_file()
        if _new_content != self._last_content:
            self._last_content = _new_content
            return True
        else:
            return False


class Build:
    build_steps = []  # type: List[object]
    watchedFiles = []  # type: List[FileWatch]

    def addWatchedFile(self, fileToAdd: str):
        self.watchedFiles.append(FileWatch(fileToAdd))

    def hasAnythingChanged(self):
        _cache = []
        for i in self.watchedFiles:
            _cache.append(i.hasItChanged())
        if True in _cache:
            return True
        else:
            return False

    def build(self):
        for i in self.build_steps:
            i()

    def addToBuild(self, nameOfCompilationStep):
        self.build_steps.append(self.build_map[nameOfCompilationStep])


class ProcessArgs:
    def __init__(
            self, argv: List[str],
            usage_func: Callable[[int, object], None],
            BuildClassToUse,
            file_auxdir_suffix: str,
            ) -> None:

        self.output = {
            "input": None,
            "disable_viewer": False,
            'slow': False,
            "file": '',
            "extra_files": [],
            "outputType": '',
        }  # type: Dict[str, Any]

        self.output_recipe = Recipe({
            'make': False,
            'file': '',
            'extra_files': [],
        })
        self.long_args_to_disc = {
                '--help': self._help,
                '--auxdir': self._auxdir,
                '--slow': self._slow,
                '--no-pdf': self._disable_viewer,
                '--files': self._extra_files,
                '--make': self._make,
                }

        self.short_args_to_disc = {
                'h': self._help,
                'a': self._auxdir,
                'S': self._slow,
                'D': self._disable_viewer,
                'f': self._extra_files,
                'm': self._make,
                }

        self.input_argv = argv
        self.usage_func = usage_func
        self.BuildClassToUse = BuildClassToUse

        self.output['auxdir'] = os.path.expandvars(
                '/tmp/$USER-' + file_auxdir_suffix)
        self.output_recipe['auxdir'] = os.path.expandvars(
                '/tmp/$USER-' + file_auxdir_suffix)
        self.output["name"] = os.path.basename(self.input_argv[0])

    # All of these run in the same scope as processargs(). They make changes to
    # output.
    def _help(self, i: int) -> None:
        try:
            self.usage_func(0, self.output['name'])
        except NameError:
            exit(0)

    def _make(self, i: int) -> None:
        self.output_recipe['make'] = True

    def _slow(self, i: int) -> None:
        self.output['slow'] = True

    def _disable_viewer(self, i: int) -> None:
        self.output['disable_viewer'] = True

    def _extra_files(self, i: int) -> None:
        if '=' in self.input_argv[i]:
            extra_file = self.input_argv[i].split('=')[1]
        else:
            extra_file = self.input_argv[i + 1]
            self.indexes_to_ignore.append(i + 1)

        self.output_recipe["extra_files"].append(
            os.path.expandvars(os.path.expanduser(extra_file)))
        self.output["extra_files"].append(
            os.path.expandvars(os.path.expanduser(extra_file)))

    def _auxdir(self, i: int) -> None:
        if '=' in self.input_argv[i]:
            auxdir = self.input_argv[i].split('=')[1]
        else:
            auxdir = self.input_argv[i + 1]
            self.indexes_to_ignore.append(i + 1)

        self.output_recipe["auxdir"] = os.path.expandvars(
                os.path.expanduser(auxdir)
                )
        self.output["auxdir"] = os.path.expandvars(os.path.expanduser(auxdir))

    # In place of a switch-case statement the following dictionaires link argv
    # entries to functions.
    def render_processargs(self) -> ProcessedArgs:
        self.indexes_to_ignore = []  # type: List[int]

        if len(self.input_argv) == 1:
            pass
        else:
            # range() starts at 1 to prevent the name from being processed.
            for i in range(1, len(self.input_argv)):
                if i in self.indexes_to_ignore:
                    continue

                elif len(self.input_argv[i]) >= 2 and \
                        self.input_argv[i][0:2] == '--':
                    try:
                        self.long_args_to_disc[
                                self.input_argv[i].split('=')[0]
                                ](i)
                    except KeyError:
                        print("Invalid argument", file=sys.stderr)
                        self.usage_func(1, self.output['name'])

                elif self.input_argv[i][0] == '-' and \
                        self.input_argv[i][1] != '-':
                    for j in range(1, len(self.input_argv[i])):
                        try:
                            self.short_args_to_disc[self.input_argv[i][j]](i)
                        except KeyError:
                            print("Invalid argument", file=sys.stderr)
                            self.usage_func(1, self.output['name'])

                elif not self.output_recipe["file"]:
                    self.output_recipe["file"] = self.input_argv[i]
                    self.output["file"] = self.input_argv[i]

                else:
                    print("Error parsing arguments", file=sys.stderr)
                    self.usage_func(1, self.output['name'])
        self.output['build'] = self.BuildClassToUse(self.output_recipe)

        return self.output
