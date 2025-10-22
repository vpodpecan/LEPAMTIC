### About

This folder contains the scripts for postprocessing of the results of LEPAMTIC. They were used for postprocessing of the LEPAMTIC results for publication.


#### Script 4 - data harmonization

##### Goal

Transform the LLM prompt chain output (extraction table) into an analysis-ready harmonized extraction table. 

##### Description 

It filters and harmonizes data rows based on single-category entries, expected values, valid driver-contrast combinations, and deduplication. It includes eight harmonization steps across multiple columns.

Script4_data_harmonization takes as input the extraction_table, which is the direct output of LLM knowledge extraction (Script1). See `extraction_table_sample.csv`. This script also uses the files `driver_contrasts_list3.csv` and `driver_contrasts_orientation2.csv` files.


#### Script 5 - gap extraction overview

##### Goal

Generate the final extraction table and data synthesis and visualization.

##### Description 

Script5_gap_extraction_overview takes as input the extraction table and also the harmonized extraction table, which is the direct output of script 4. See `harmonized_extraction_table_sample.csv`

In **part (A)** we check the “extraction table” and examine it in detail. In **part (B)** we check the “harmonized extraction table”. In **part (C)** we then take the harmonized extraction table and, in a series of structured steps, review each key extraction element to filter NAs, remove redundancies, and tailor the dataset to the study’s focal gaps—biochar and the retention of crop residues versus soil fauna. The final output is the
"final extraction table". In **part (D)** we check the "final extraction table", describe the final results from several perspectives and build the final plots
