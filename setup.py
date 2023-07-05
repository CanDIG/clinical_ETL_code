import setuptools

setuptools.setup(name="candigv2-etl",
                 version="1.0.1",
                 python_requires=">=3.10",
                 install_requires=[
                    "pandas~=1.3.4",
                    "httplib2~=0.20.2",
                    "biopython",
                    "pytest==7.2.0",
                    "pyYAML~=5.4.1",
                    "dateparser~=1.1.0",
                    "openpyxl~=3.0.9",
                    "jsoncomparison~=1.1.0",
                    "requests>=2.26.0",
                    "jsonschema~=3.2.0"
                 ],
                 packages=["candigETL"],
                 description="CanDIG candigETL module for transforming phenotypic CSV data into Katsu packets",
                 url="https://github.com/CanDIG/clinical_ETL_code"
                 )
