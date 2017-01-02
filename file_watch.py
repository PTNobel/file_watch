#!/usr/bin/python3

import latex_watch
import pandoc_watch
import sys
import os
from threading import Thread
from typing import List, Tuple, Dict, Any, Callable

ProcessedArgs = Dict[str, Any]
MainForFileMethod = Callable[[ProcessedArgs], None]
FilePair = Tuple[MainForFileMethod, ProcessedArgs]


def processargs(
        argv: List[str],
        ) -> List[FilePair]:
    output = list()  # type: List[FilePair]
    dashArguments = False
    markdownFiles = False
    latexFiles = False
    # Skip the name of the program
    for arg in argv[1:]:
        if arg[0] == '-':
            dashArguments = True
        elif '.md' in arg[-3:]:
            markdownFiles = True
        elif '.tex' in arg[-4:]:
            latexFiles = True

    if not dashArguments and len(argv) > 1:
        for arg in argv[1:]:
            if '.md' in arg[-3:]:
                output.append(
                        (
                            pandoc_watch.main_for_file,
                            pandoc_watch.processargs([argv[0], arg])
                        )
                )

            elif '.tex' in arg[-4:]:
                output.append(
                        (
                            latex_watch.main_for_file,
                            latex_watch.processargs([argv[0], arg])
                        )
                )

    elif markdownFiles and latexFiles:
        exit(1)
    elif markdownFiles:
        output.append(
                (
                    pandoc_watch.main_for_file,
                    pandoc_watch.processargs(argv)
                )
        )

    elif latexFiles:
        output.append(
                (
                    latex_watch.main_for_file,
                    latex_watch.processargs(argv)
                )
        )
    else:
        # No file name given
        for file_name in os.listdir():
            if len(file_name) > 9 and file_name[0] == '.' and \
                    file_name[-8:] == '.tex.swp':
                output.append(
                        (
                            latex_watch.main_for_file,
                            latex_watch.processargs(argv + [file_name[1:-4]])
                        )
                )

            if len(file_name) > 8 and file_name[0] == '.' and \
                    file_name[-7:] == '.md.swp':
                output.append(
                        (
                            pandoc_watch.main_for_file,
                            pandoc_watch.processargs(argv + [file_name[1:-4]])
                        )
                )
    return output


def launchWatches(mainsAndArgs: List[FilePair]) -> None:
    for mainAndArgPair in mainsAndArgs:
        Thread(
            target=mainAndArgPair[0],
            args=tuple([mainAndArgPair[1]]),
            ).start()


if __name__ == '__main__':
    launchWatches(processargs(sys.argv))
