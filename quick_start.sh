#!/bin/bash
# Quick start: run the converter on the sample config and show what to do next.
# This script demonstrates the workflow. It is not part of the converter.

set -e

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

if [ ! -f "panorama_to_terraform.py" ]; then
    echo "Error: panorama_to_terraform.py not found in the current directory."
    exit 1
fi

if [ ! -f "sample_panorama_config.xml" ]; then
    echo "Error: sample_panorama_config.xml not found in the current directory."
    exit 1
fi

# Pass --validate so the post-run gate also runs terraform init and validate.
# The gate reports the checks it cannot run when the terraform binary is absent,
# so the run still completes.
VALIDATE_FLAG=""
if command -v terraform &> /dev/null; then
    VALIDATE_FLAG="--validate"
fi

echo "Running the example conversion..."
echo ""

python3 panorama_to_terraform.py sample_panorama_config.xml \
    --output-dir terraform_example $VALIDATE_FLAG

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
echo "The exit code is 1 when a gate check FAILs, so a failed run does not look"
echo "like a success. See docs/USAGE_GUIDE.md for the flags and the reports."
