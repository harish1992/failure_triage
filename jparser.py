import sys
import argparse
import json
from jp_ollama import JpAiTool, JpResponseError
from lxml.etree import XMLParser, parse
from junitparser import JUnitXml, Failure, Error, Skipped
from pathlib import Path
from jp_report import JpHtmlReport

def argparser() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("patterns", nargs = "+", type=Path)
    parser.add_argument('-o', "--output", default="junit-triaged.xml")
    parser.add_argument('-m', "--model", default='granite3.1-dense:8b')
    args = parser.parse_args()
    return args

class AiTriage:
    def __init__(self, input_pattern, output_file, aiInstance):
        self.cache = {}
        self.patterns = input_pattern
        self.out = output_file
        self.aiInstance = aiInstance

    def parse_func(self, file_path):
        xml_parser = XMLParser(huge_tree=True)
        return parse(file_path, xml_parser)

    def load(self, patterns, outputfile):
        files = sorted(
            f for pattern in patterns for f in Path(pattern.parent).glob(pattern.name)
            if Path(f).suffix == '.xml' and Path(f).name != Path(outputfile).name
        )
        if not files:
            sys.exit(f"no input files matched {patterns}")
        print(f"merging {len(files)} file(s): {[f.name for f in files]}")
        merged = None
        for f in files:
            suite = JUnitXml.fromfile(f, self.parse_func)
            merged = suite if merged is None else merged + suite
        return merged

    def get_err_string(self, text: str) -> str:
        i = text.rfind("Error")
        return text[i:] if i != -1 else text

    def triage_helper(self, case, failure) -> str:
        # find the actual error and create a digest index for cache
        failtext =  (failure.text or failure.message or '').strip()
        ai_read = False
        error_metadata = f"{case.classname}.{case.name}"
        # skip interpreting if the test is already interpreted
        # that is multiple rerun, this value will never be None
        cache_res = self.cache.get(error_metadata)
        if cache_res is not None:
            result_array, ai_read = cache_res
            if ai_read:
                return f"skipping for {error_metadata} as its already read and interpreted"

        #ask ai to decode the error
        prompt =  f"Test: {case.classname}.{case.name}\n" \
                  f"Type: {failure.type}\nMessage: {failure.message}\n\n{failtext[:6000]}\n" \
                  f"result_array : {result_array}\n" 
        try:
            resp = self.aiInstance.ask(prompt)
        except JpResponseError as e:
            raise e
        message =  resp['message']['content'].strip() if resp else ""
        try: 
            message = json.dumps({"test_case": error_metadata, **json.loads(message), 
                              "stack_trace": failtext}, indent=4)
        except:
            print(f"Message: {message} is not JSON object")
        self.cache[error_metadata] = (result_array, True) 
        return message
    
    def parse_test_cases(self, xml):
        for suite in xml:
            for case in suite:
                yield case

    def parse_error_cases(self, xml):
        for case in self.parse_test_cases(xml):
            yield from ((case,r) for r in case.result if isinstance(r, (Failure, Error)))
    
    def cache_init(self, case):
        error_metadata = f"{case.classname}.{case.name}"
        result = "Pass"
        for r in case.result:
            if isinstance(r, Failure):
                result = "Failure"
            elif isinstance(r, Skipped):
                result = "Skip"
            elif isinstance(r, Error):
                result = "Error"

        if self.cache.get(error_metadata) is None:
            self.cache[error_metadata] = ([result] , False) #([result], ai-read)
        else:
            result_array, ai_read = self.cache[error_metadata]
            self.cache[error_metadata] =  ([*result_array, result], ai_read)

    def triage(self):
        all_data = []
        report = JpHtmlReport()
        xml = self.load(self.patterns, self.out)
        for case in self.parse_test_cases(xml):
            self.cache_init(case)
        print(self.cache)
        for case, r in self.parse_error_cases(xml):
            desc = self.triage_helper(case, r)
            print(desc)
            all_data.append(json.loads(desc))
        # write to a JSON file
        with open(self.out, "w") as f:
            json.dump(all_data, f, indent=4)
        report.html_report(f"{Path(self.out).stem}.html", json_data=all_data)

if __name__ == "__main__":
    args = argparser()
    ai_inst = JpAiTool(args.model)
    triage_failure = AiTriage(args.patterns, args.output, ai_inst)
    triage_failure.triage()
