#!/bin/bash
# Quick start: run the converter on the committed sample export and show what to do next.
# This script demonstrates the workflow. It is not part of the converter.

set -e

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# The layout rule (`docs/ARCHITECTURE.md` §1.1): the tool's modules are in `src/` and the sample input is in
# `examples/`. Both are read from the repository root, so the script runs from any directory.
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONVERTER="$REPO_ROOT/src/panorama_to_terraform.py"
SAMPLE="$REPO_ROOT/examples/sample_panorama_config.xml"

if [ ! -f "$CONVERTER" ]; then
    echo "Error: src/panorama_to_terraform.py not found under the repository root."
    exit 1
fi

if [ ! -f "$SAMPLE" ]; then
    echo "Error: examples/sample_panorama_config.xml not found under the repository root."
    exit 1
fi

# The script asks for each gate check that runs an external command when that binary is present, so
# a run through the script reports the result of every check it can run. The gate reports a check it
# was not asked for as NOT RUN, so without this the demonstration reports the rule set as not run on
# a machine that has the tool. What a run reports for each check is the gate's rule, in
# `docs/ARCHITECTURE.md` §4.6, which this comment does not restate.
FLAGS=()
if command -v terraform &> /dev/null; then
    FLAGS+=("--validate")
fi
if command -v tflint &> /dev/null; then
    FLAGS+=("--tflint")
fi

echo "Running the example conversion..."
echo "Flags this run asks for: ${FLAGS[*]:-none}"
echo ""

python3 "$CONVERTER" "$SAMPLE" --output-dir terraform_example "${FLAGS[@]}"

echo ""
echo "Conversion complete. Output is in ./terraform_example/"
echo ""
echo "Next steps:"
echo "  1. cd terraform_example"
echo "  2. Read the reports: CONVERSION_REPORT.txt, MANUAL_SETUP_REPORT.txt,"
echo "     INTERFACE_MIGRATION_REPORT.txt, VPN_MIGRATION_REPORT.txt, SANITY_REPORT.txt"
echo "  3. Create terraform.tfvars with the Panorama credentials:"
echo ""
echo "     panos_hostname = \"your-panorama-hostname\""
echo "     panos_username = \"admin\""
echo "     panos_password = \"your-password\""
echo ""
echo "  4. terraform init"
echo "  5. terraform plan"
echo "  6. terraform apply"
echo ""
echo "SANITY_REPORT.txt names each check that runs an external command, for this run:"
echo "  the result for a check this run asked for, NOT RUN for one it did not ask for,"
echo "  and SKIPPED for one asked for by name with no binary."
echo "The gate rule is in docs/ARCHITECTURE.md §4.6."
echo ""
echo "The exit code is 1 when a gate check FAILs, so a failed run does not look like a success."
echo "See docs/USAGE_GUIDE.md in the repository root for the flags and the reports."
