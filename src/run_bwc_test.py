#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

import logging
import sys

from manifests.bundle_manifest import BundleManifest
from system import console
from system.temporary_directory import TemporaryDirectory
from test_workflow.bwc_test.bwc_test_suite import BwcTestSuite
from test_workflow.test_args import TestArgs


def main():
    args = TestArgs()
    console.configure(level=args.logging_level)
    with TemporaryDirectory(keep=args.keep) as work_dir:
        logging.info(f"Switching to temporary work_dir: {work_dir.name}")
        bundle_manifest = BundleManifest.from_s3(
            args.s3_bucket,
            args.build_id,
            args.opensearch_version,
            args.architecture,
            work_dir.name,
        )
        BwcTestSuite(bundle_manifest, work_dir.name, args.component, args.keep).execute()


if __name__ == "__main__":
    sys.exit(main())
