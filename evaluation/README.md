### About

This folder contains the scripts for the evaluation of the results of LEPAMTIC. They were used for the evaluation of the LEPAMTIC results for publication.


#### Program6_LLM_extraction_evaluation

##### Goal

The evaluation of the performance of the prompt chain in both extraction and unification stages, using expert extractions and annotations as the reference.
`Program6_LLM_extraction_evaluation` takes as input the expert annotator evaluations, which were built on the LLM extraction results. See `expert_evaluation_sample.csv`


#### Program5_models_evaluation

##### Goal

Alternative LLMs' performance assessed through an objective quantitative analysis of an LLM-based subjective evaluation.
`Program5_models_evaluation` takes as input the expert annotator evaluations and the extraction done by alternative LLMs than the one used in this study(ChatGPT4.o - OpenAI). See `alternative_LLM_extraction_sample.csv`