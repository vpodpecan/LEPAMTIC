### About
This folder contains the script for postprocessing of the results of LEPAMTIC. They were used for postprocessing of the LEPAMTIC results for publication.

#### Program2_module_4

##### Goal

Transform the LLM prompt chain output (extraction table) into an analysis-ready harmonized extraction table.

##### Description

It filters and harmonizes data rows based on single-category entries, expected values, valid driver-contrast combinations, and deduplication. It includes eight harmonization steps across multiple columns.

`Program2_module_4` takes as input the extraction_table, which is the direct output of LLM knowledge extraction (Script1). See `extraction_table_sample.csv`. 

This script also uses the files `driver_contrasts_list.csv` and `driver_contrasts_orientation.csv` files. 
