# LEPAMTIC

## About

LEPAMTIC is a methodology for pattern extraction from scientific abstracts using large language models (LLMs).
It extracts specific patterns about the effects of land management practices on soil biota.

The prompts are currently tailored to two focal gaps: **biochar** and **retaining crop residues** versus **soil fauna**, but can be easily modified to other combinations of land management practices and soil biota.


The name comes from the type of the pattern it extracts:

**L**: Land management practice (e.g., conventional tillage)  
**E**: Effect (e.g., increase, decrease, no effect)  
**P**: Affected property of soil biota (e.g., diversity, abundance)  
**A**: Soil biota actor (e.g., bacteria, fungi, nematodes)  
**M**: Measurement method (e.g., qPCR, Shannon diversity index)  
**T**: Temporal scope (e.g., timing after treatment)  
**I**: Locational scope (e.g., soil depth, field site)  
**C**: Contrasting practice (e.g. no tillage) 

## How to use

You need Python 3.9+ and packages listed in `requirements.txt`.


### Requirements

#### LLM
You can use OpenAI API, Google API or local models (ollama). When using OpenAI or Google API, save the API key into a file which will be read by the extractor. 
When using local models, set the `base_url` parameter which points to your local server hosting the model.

#### Input data
The extractor accepts `.csv` and `.xlsx` files with at least two columns: primary key and abstract.
The primary key column must be unique and nonempty for all rows, e.g., DOI, Pubmed ID, Accession Number, etc.
In most cases the input data is a table exported from WOS or Scopus.


#### Preparing the environment

1. Create and activate a virtual environment.

    - Linux
      ```bash
      python3 -m venv myEnv
      source myEnv/bin/activate
      ```
  
    - Windows
      ```bash
      python3 -m venv myEnv
      myEnv\Scripts\activate
      ```
      
2. Clone the repository
    ```bash
    git clone https://github.com/vpodpecan/LEPAMTIC.git
    ```

### Running LEPAMTIC

The complete procedure of knowledge extraction consists of several steps of which the first one is the actual LEPAMTIC pipeline while the rest of the steps are optional but perform important tasks of postprocessing and evaluation.

1. Running the LEPAMTIC extractor using GPT-4o model and sample data:

    ```bash
    python3 extractor.py extract --model_name gpt-4o --scoring_model_name o3 --actor_file data/LLM_actors_list_V2.csv --input_file data/sample.xlsx --output_dir results --openai_keyfile api_keys/openai_api_key --primary_key "UT (Unique ID)" --abstract_column "Abstract"
    ```
    There are two additional modes: `screen` and `score`. `screen` prescreens the input data to find out which abstracts should be considered for the long and costly extraction.
   `score` scores the abstracts according to LEPAMTIC rules.


2. Postprocessing (optional):
    
   The scripts for this step are located in folder `postprocessing`. The goal is to transform the result of the LEPAMTIC pipeline (extraction table) into an analysis-ready harmonized extraction table. A script to generate the final extraction table and data synthesis and visualization is also provided.


5. Evaluation (optional): 
   
   The scripts for this step are located in folder `evaluation`. The goal is the evaluation of the performance of the LEPAMTIC prompt chain in both extraction and unification stages, using expert extractions and annotations as the reference.



## Authors

The core of LEPAMTIC is developed by Vid Podpečan (vid.podpecan@ijs.si).

The evaluation scripts were developed by Martina Lori (martina.lori@fibl.org) and Ricardo Leitão (ricveigaleitao@gmail.com).

The postprocessing scripts were developed by Luis Cunha (luis.cunha@uc.pt), Martina Lori, and Ricardo Leitão.


## License

MIT
