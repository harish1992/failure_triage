import sys
from pathlib import Path
from lxml.etree import XMLParser, parse
from junitparser import JUnitXml, Failure, Error, Skipped

class JpJunitLoader:
    def parse_func(self, file_path):
        xml_parser = XMLParser(huge_tree=True)
        return parse(file_path, xml_parser)

    def load(self, patterns):
        files = sorted(
            f for pattern in patterns for f in Path(pattern.parent).glob(pattern.name)
            if Path(f).suffix == '.xml'
        )
        if not files:
            sys.exit(f"no input files matched {patterns}")
        print(f"merging {len(files)} file(s): {[f.name for f in files]}")
        merged = None
        for f in files:
            suite = JUnitXml.fromfile(f, self.parse_func)
            merged = suite if merged is None else merged + suite
        return merged
    
    def __init__(self, patterns: Path) -> None:
        self._xml_data = self.load(patterns=patterns)
    
    def parse_test_cases(self):
        for suite in self._xml_data:
            for case in suite:
                yield case

    def parse_error_cases(self):
        for case in self.parse_test_cases():
            yield from ((case,r) for r in case.result if isinstance(r, (Failure, Error)))