#
# SPDX-FileCopyrightText: 2023 DRAIVE GmbH <copyright@draive.com>
#

import sys
import os
import logging
import importlib.util

from lara.logger import logger
from lara.api.repository import Repository


def load_verification_rules(base_folder: str):
    result = list()
    folder = os.path.join(base_folder, "rules")
    for rule in os.listdir(folder):
        path = os.path.join(folder, rule)
        if not rule.endswith(".py"):
            continue
        try:
            rule_spec = importlib.util.spec_from_file_location("template.verify", path)
            rule_module = importlib.util.module_from_spec(rule_spec)
            rule_spec.loader.exec_module(rule_module)

            result.append((os.path.splitext(rule)[0], rule_module))
        except Exception as e:
            logger.error("Unable to load verification script '{}'".format(path))
            logger.error("  - error: {}; {}".format(e.__class__, e.args))
            logger.error("  - path: {}".format(path))
            return None

    return result

def main_verify(config):
    if len(config.repo_folder) == 0:
        # This won't happen when liam is called directly using the command line.
        # However this may happen when liam is called from another tool.
        logger.warning("No repository path given. Defaulting to current directory.")
        config.repo_folder = "."

    repository = Repository.load(config.repo_folder)
    logger.info('Repository uses template {}={}'.format(repository.template, repository.current_revision))

    # checkout the matching revision
    verification_rules = load_verification_rules(os.path.dirname(os.path.abspath(__file__)))
    if not verification_rules:
        return 1

    rules_ok = 0
    rules_bad = 0
    for (rule_name, rule_module) in verification_rules:
        try:
            # call the verification script
            (errors, warnings) = rule_module.verify(repository, config.repo_folder)

            success = len(errors) == 0
            warnings_present = len(warnings) != 0
            if success:
                rules_ok += 1
                if not warnings_present:
                    logger.info("Rule \"{}\" verified successfully.".format(rule_name))
                else:
                    logger.warning("Rule \"{}\" verified successfully, but there are warnings.".format(rule_name))
                    for e in warnings:
                        logger.warning("  - {}".format(e))
            else:
                rules_bad += 1
                logger.error("Rule \"{}\" failed to verify.".format(rule_name))
                for e in errors:
                    logger.error("  - {}".format(e))
                for e in warnings:
                    logger.warning("  - {}".format(e))
        except Exception as e:
            rules_bad += 1
            logger.error("Unable to execute verification script {}: {}: {}".format(rule_module, e.__class__, e.args))
            if config.debug_template_package:
                raise e

    if rules_bad == 0:
        logger.info("Verification completed successfully. Rules checked: {}".format(rules_ok))
        return 0
    else:
        logger.info("Verification failed. Successful rules: {}, failed rules: {}".format(rules_ok, rules_bad))
        return 1

class Config(object):
    def __init__(self, **kwargs):
        self.repo_folder = os.path.curdir
        self.debug_template_package = False
        self.verbose = False

def main():
    config = Config()
    if len(sys.argv) >= 2:
        config.repo_folder = sys.argv[1]

    logger.setLevel(logging.INFO)
    if config.verbose:
        logger.setLevel(logging.DEBUG)
    try:
        return main_verify(config)
    except Exception as e:
        logger.error("Operation failed: " + str(e))
        # if in development mode, re-raise the error
        if config.debug_template_package:
            raise e
    return 1


if __name__ == "__main__":
    exit(main())
