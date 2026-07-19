# Wetland Redox Workbench

Project documentation and support tools for wetland redox
modeling with ELM, PFLOTRAN, and Alquimia.

## Documentation

The documentation is built with Sphinx and MyST Markdown.

```bash
conda env create -f environment_dev.yml
conda activate wetland-redox-workbench
make docs
```

## ELM-PFLOTRAN Runtime Environment

The Cardinal ELM-PFLOTRAN-Alquimia runtime environment is recorded in
`environment.yml`. The module and library setup script is:

```bash
source scripts/setup_env.sh
```
