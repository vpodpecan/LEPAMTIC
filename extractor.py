import pandas as pd
import LEPAMTIC as lepamtic

import os
import argparse
import sys
from datetime import datetime

import traceback
from json import JSONDecodeError

from chat_via_api import ChatDialog

# from importlib import reload
# reload(lepamtic)


def get_LLM(model_name, args):
    role = 'You act as a data scientist specialized in text mining. Your research domain is soil health, soil biology and land management practices.'

    if 'gpt' in model_name or 'o3' in model_name or 'o4' in model_name or 'o1' in model_name:
        if not args.openai_keyfile:
            raise ValueError(f'{model_name} needs the "--openai_keyfile" parameter to be set')

        llm = ChatDialog(api_key=open(args.openai_keyfile).read().strip(),
                        organization='org-ZrgvzvWlbLIRYMeUAOrVk3am',  # this is optional
                        model=model_name,
                        role=role,
                        call_wait_time=1,
                        reset_for_each_call=False)
    
    elif 'gemini' in model_name:
        if not args.openai_keyfile:
            raise ValueError(f'{model_name} needs the "--google_keyfile" parameter to be set')

        llm = ChatDialog(api_key=open(args.google_keyfile).read().strip(),
                        base_url='https://generativelanguage.googleapis.com/v1beta/openai/',
                        model=model_name,
                        role=role,
                        call_wait_time=15,
                        reset_for_each_call=False)    
    
    else:
        raise ValueError('Please set the parameters of the local LLM in the code')
        llm = ChatDialog(base_url="",
                        api_key = "ollama",
                        model=model_name,
                        role=role,
                        call_wait_time=1,
                        reset_for_each_call=False)
    return llm


def read_data(fname):
    name, ext = os.path.splitext(fname)
    ext = ext.lower()
    if ext in ['.xls', '.xlsx']:
        df = pd.read_excel(fname)
    elif ext == '.csv':
        df = pd.read_csv(fname)

    orig_len = len(df)

    if 'Abstract' not in df.columns:
        raise SyntaxError('"Abstract" column not present')
    if 'DOI' not in df.columns:
        raise SyntaxError('"DOI" column not present')

    # exclude empty abstracts
    df = df[(df['Abstract'].notna()) & (df['Abstract']!='')]

    if (nempty := orig_len - len(df)) > 0:
        print(f'Warning: {nempty} empty abstract(s) ignored!')

    # fill missing DOIs
    mask = (df['DOI'] == '') | (df['DOI'].isna())
    df.loc[mask, 'DOI'] = [f'missing_DOI_{i+1}' for i in range(mask.sum())]
    if (miss := sum(mask)) > 0:
        print(f'Warning: {miss} missing DOIs filled in!')
    return df


def store_error(error_data):
    error_text = traceback.format_exc()
    error_data.append({'DOI': doi, 'error': error_text})


if __name__ == '__main__':

    def add_common_args(subparser):
        subparser.add_argument('--output_dir', type=str, required=True, help='Directory to store output files')
        subparser.add_argument('--input_file', type=str, required=True, help='Path to the input CSV file')
        subparser.add_argument('--seed', type=int, required=False, default=42, help='LLM seed parameter (read LLM docs for more info)')
        subparser.add_argument('--temperature', type=float, required=False, default=0, help='LLM temperature parameter (read LLM docs for more info)')
        subparser.add_argument('--reasoning_effort', type=str, required=False, choices=['low','medium','high'], default='medium', help='The reasoning_effort parameter (OpenAI reasoning models only)')
        subparser.add_argument('--n_repeats', type=int, required=False, default=10, help="Number of retries if the model's output is invalid")
        subparser.add_argument('--openai_keyfile', type=str, required=False, help="A file containing OpenAI API key")
        subparser.add_argument('--google_keyfile', type=str, required=False, help="A file containing Google API key")

    parser = argparse.ArgumentParser(description='Run LLM processing on CSV input.')
    subparsers = parser.add_subparsers(dest="mode", required=True, help="Select a mode to run")

    screen_parser = subparsers.add_parser("screen", help="Run prescreening mode")
    screen_parser.add_argument('--model_name', type=str, required=True, help='Name of the LLM model to use (e.g., gpt-4)')
    add_common_args(screen_parser)

    extract_parser = subparsers.add_parser("extract", help="Run extraction mode")
    extract_parser.add_argument('--model_name', type=str, required=True, help='Name of the LLM model to use (e.g., gpt-4)')
    extract_parser.add_argument('--scoring_model_name', type=str, required=True, help='Name of the LLM model to use for scoring abstracts (e.g., o3)')
    extract_parser.add_argument('--actor_file', type=str, required=True, help='Path to the actor CSV file')
    add_common_args(extract_parser)

    score_parser = subparsers.add_parser("score", help="Run scoring mode")
    score_parser.add_argument('--scoring_model_name', type=str, required=True, help='Name of the LLM model to use for scoring abstracts (e.g., o3)')
    add_common_args(score_parser)
    
    args = parser.parse_args()
    args.seed = None


    # Validate input file
    if not os.path.isfile(args.input_file):
        print(f"Error: Input file '{args.input_file}' does not exist.", file=sys.stderr)
        sys.exit(1)

    # Validate output directory
    if not os.path.isdir(args.output_dir):
        print(f"Error: Output directory '{args.output_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)


    if args.mode == 'screen':
        llm = get_LLM(args.model_name, args)

        original_data = read_data(args.input_file)
        data = original_data[['DOI', 'Abstract']].copy()
        data['DOI'] = data['DOI'].str.lower()
        data = data.set_index('DOI')

        error_data = []
        results = []

        for doi, row in data.iterrows():
            abstract = row['Abstract']
            # try n_repeats fimes to get over some erratic one-time-only behaviour of LLMs
            for cnt in range(args.n_repeats):
                try:
                    llm.reset()
                    score = lepamtic.prescreen(llm, abstract, seed=args.seed, temperature=args.temperature)[0]
                except JSONDecodeError as e:
                    print(e)
                    print(f'Error, attempt {cnt+1} of {args.n_repeats}')
                else:
                    results.append({'DOI': doi, 'abstract_relevance': score['relevance'], 'abstract_relevance_explanation': score['comment']})
                    break
            else:
                store_error(error_data)                
                print(f'Error while screening {doi}')
                continue
        
        results_df = pd.DataFrame(results).set_index('DOI')
        original_data = original_data.set_index('DOI')
        output_df = original_data.merge(results_df, how='left', left_index=True, right_index=True)
        output_df = output_df.reset_index()
        
        ifn = os.path.split(args.input_file)[1]
        ifnb, ifnext = os.path.splitext(ifn)
        output_df[output_df['abstract_relevance']==1].to_csv(os.path.join(args.output_dir, f"{ifnb}__relevance_1.csv"), index=False)
        output_df[output_df['abstract_relevance']==0].to_csv(os.path.join(args.output_dir, f"{ifnb}__relevance_0.csv"), index=False)    

        errors_df = pd.DataFrame(error_data)
        if len(errors_df):
            errors_df.to_excel(os.path.join(args.output_dir, f"{ifnb}__errors.csv"), index=False)

    elif args.mode == 'score':
        scoring_llm = get_LLM(args.scoring_model_name, args)

        original_data = read_data(args.input_file)
        data = original_data[['DOI', 'Abstract']].copy()
        data['DOI'] = data['DOI'].str.lower()
        data = data.set_index('DOI')

        error_data = []
        results = []

        for doi, row in data.iterrows():
            abstract = row['Abstract']
            # try n_repeats fimes to get over some erratic one-time-only behaviour of LLMs
            for cnt in range(args.n_repeats):
                try:
                    scoring_llm.reset()
                    score = lepamtic.extract_score(scoring_llm, abstract, seed=args.seed, temperature=args.temperature)[0]
                except JSONDecodeError as e:
                    print(e)
                    print(f'Error, attempt {cnt+1} of {args.n_repeats}')
                else:
                    results.append({'DOI': doi, 'abstract_score': score['score'], 'abstract_score_explanation': score['score_explanation']})
                    break
            else:
                store_error(error_data)                
                print(f'Error while scoring {doi}')
                continue
        
        results_df = pd.DataFrame(results).set_index('DOI')
        original_data = original_data.set_index('DOI')
        output_df = original_data.merge(results_df, how='left', left_index=True, right_index=True)
        output_df = output_df.reset_index()
        
        ifn = os.path.split(args.input_file)[1]
        ifnb, ifnext = os.path.splitext(ifn)
        output_df.to_csv(os.path.join(args.output_dir, f"{ifnb}__scored.csv"), index=False)

        errors_df = pd.DataFrame(error_data)
        if len(errors_df):
            errors_df.to_excel(os.path.join(args.output_dir, f"{ifnb}__errors.csv"), index=False)

    else: # args.mode == 'extract':
        if not os.path.isfile(args.actor_file):
            print(f"Error: Actor file '{args.actor_file}' does not exist.", file=sys.stderr)
            sys.exit(1)

        ##################
        # The main part is here instead of in a function for easy debugging

        llm = get_LLM(args.model_name, args)
        scoring_llm = get_LLM(args.scoring_model_name, args)

        unified_actors = pd.read_csv(args.actor_file, header=None)[0].to_list()

        data = read_data(args.input_file)
        data = data[['DOI', 'Abstract']].copy()
        data['DOI'] = data['DOI'].str.lower()
        data = data.set_index('DOI')

        error_data = []
        result_dfs = []
        for doi, row in data.iterrows():
            abstract = row['Abstract']

            # try every step n_repeats fimes to get over some erratic one-time-only behaviour of LLMs
            for cnt in range(args.n_repeats):
                try:
                    scoring_llm.reset()
                    score = lepamtic.extract_score(scoring_llm, abstract, seed=args.seed, temperature=args.temperature)[0]
                except JSONDecodeError as e:
                    print(e)
                    print(f'Error, attempt {cnt+1} of {args.n_repeats}')
                else:
                    break
            else:
                store_error(error_data)                
                print(f'Error while scoring {doi}')
                continue


            for cnt in range(args.n_repeats):
                try:
                    llm.reset()
                    patterns_df = pd.DataFrame(lepamtic.extract_patterns(llm, abstract, seed=args.seed, temperature=args.temperature))
                    patterns_df.insert(0, 'DOI', doi)
                except JSONDecodeError as e:
                    print(e)
                    print(f'Error, attempt {cnt+1} of {args.n_repeats}')
                else:
                    break
            else:
                store_error(error_data)                
                print(f'Error while finding patterns for {doi}')
                continue


            for cnt in range(args.n_repeats):
                try:
                    llm.reset()
                    uactors_df = pd.DataFrame(lepamtic.unify_actors(llm, patterns_df['actor'].to_list(), unified_actors, seed=args.seed, temperature=args.temperature))
                    patterns_df.insert(7, 'actor_unified', uactors_df['actor_unified'])
                except JSONDecodeError as e:
                    print(e)
                    print(f'Error, attempt {cnt+1} of {args.n_repeats}')
                else:
                    break
            else:
                store_error(error_data)                
                print(f'Error while unifying actors for {doi}')
                continue


            for cnt in range(args.n_repeats):
                try:
                    llm.reset()
                    uproperties_df = pd.DataFrame(lepamtic.unify_property(llm, patterns_df['property'].to_list(), lepamtic.unified_properties, seed=args.seed, temperature=args.temperature))
                    patterns_df.insert(6, 'property_unified', uproperties_df['property_unified'])
                except JSONDecodeError as e:
                    print(e)
                    print(f'Error, attempt {cnt+1} of {args.n_repeats}')
                else:
                    break
            else:
                store_error(error_data)                
                print(f'Error while unifying property for {doi}')
                continue

            patterns_df.insert(len(patterns_df.columns), 'score', score['score'])
            patterns_df.insert(len(patterns_df.columns), 'score_explanation', score['score_explanation'])
            result_dfs.append(patterns_df)


        if result_dfs:
            columns = set(result_dfs[0].columns)
            for df in result_dfs[1:]:
                if set(df.columns) != columns:
                    print('ERROR: columns do not match across all extraction results! NaNs will be present after concatenation.')


        patterns_df = pd.concat(result_dfs, ignore_index=True)
        errors_df = pd.DataFrame(error_data)

        ##################

        base_fn = f"{args.model_name}__{datetime.now().strftime('%Y-%b-%d_%H-%M-%S')}.xlsx"
        # patterns_df, errors_df = extract_patterns(args)
        patterns_df.to_excel(os.path.join(args.output_dir, f'patterns__{base_fn}'), index=False)
        if len(errors_df):
            errors_df.to_excel(os.path.join(args.output_dir, f'errors__{base_fn}'), index=False)

        print('Finished.')
