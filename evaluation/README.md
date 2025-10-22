### About

This folder contains the scripts for the evaluation of the results of LEPAMTIC. They were used for the evaluation of the LEPAMTIC results for publication.


#### Script 2 - LLM extraction evaluation 

##### Goal

The evaluation of the performance of the prompt chain in both extraction and unification stages, using expert extractions and annotations as the reference.
Script2_LLM_extraction_evaluation takes as input the expert annotator evaluations, which were built on the LLM extraction results. See `expert_evaluation_sample.csv`


#### Script 3 - models evaluation

##### Goal

Alternative LLMs' performance assessed through an objective quantitative analysis of an LLM-based subjective evaluation.
Script3_models_evaluation takes as input the expert annotator evaluations and the extraction done by alternative LLMs than the one used in this study(ChatGPT4.o - OpenAI). See `alternative_LLM_extraction_sample.csv`