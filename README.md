# LEPAMTIC

## About

LEPAMTIC is a methodology for pattern extraction from scientific abstracts using large language models (LLM).
It extracts specific patterns about the effects of land management practices on soil biota.

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
When using local models, set the `base_url` in the script to point to your local server hosting the model

#### Input data
The extractor accepts `.csv` and `.xlsx` files with at least `Abstract` and `DOI` columns. 
`DOI` serves as an identifier, it can be incomplete in which case the missing values will be filled out with unique strings.
In most cases the input will be a table exported from WOS or Scopus.


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
3. Run the extractor
    ```bash
    python3 extractor.py extract --model_name gpt-4o --scoring_model_name o3 --actor_file data/LLM_actors_list_V2.csv --input_file my_data.csv --output_dir results --openai_keyfile api_keys/openai_api_key
    ```
    There are two additional modes: `screen` and `score`. `screen` prescreens the input data to find out which abstracts should be considered for the long and costly extraction.
   'score' scores the abstracts according to LEPAMTIC rules.


## Authors

LEPAMTIC is developed by Vid Podpečan (vid.podpecan@ijs.si).

## License

MIT
