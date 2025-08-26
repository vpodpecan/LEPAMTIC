import json


pattern_fields = ['land_management_practice', 'land_management_practice_category', 'land_management_practice_unified', 'effect', 'property', 'actor', 'method_or_measurement', 'temporal_scope', 'locational_scope', 'contrasting_land_management_practice', 'contrasting_land_management_practice_category', 'contrasting_land_management_practice_unified', 'location_country', 'study_type', 'sentences', 'comment']

pattern_fields_quoted = ['"land_management_practice"', '"land_management_practice_category"', '"land_management_practice_unified"', '"effect"', '"property"', '"actor"', '"method_or_measurement"', '"temporal_scope"', '"locational_scope"', '"contrasting_land_management_practice"', '"contrasting_land_management_practice_category"', '"contrasting_land_management_practice_unified"', '"location_country"', '"study_type"', '"sentences"', '"comment"']

unified_properties = ['diversity', 'abundance', 'activity', 'ecological index', 'biomass']



def parse_JSONL(s, required_fields=None):
    jsons = []
    for x in s.split('\n'):
        x = x.strip()
        if not x.startswith('{'):
            continue
        try:
            jsons.append(json.loads(x))
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f'Error: invalid JSON: "{x}"', e.doc, e.pos)

    if required_fields:
        for j in jsons:
            diff = set(required_fields) - set(j.keys())
            if diff:
                raise json.JSONDecodeError(f'Invalid JSONL line: missing keys {diff}', str(j), 0)
    return jsons


def prescreen(llm, abstract, **kwargs):
    prompt = f'''1. Objective
You are screening scientific abstracts that describe how land management practices affect soil biota. We aim to identify abstracts suitable for structured data extraction.

2. Target Extraction Template
Each relevant abstract should enable extraction of the following elements:

L: Land management practice (e.g., conventional tillage)
E: Effect (e.g., increase, decrease, no effect)  
P: Affected property of soil biota (e.g., diversity, abundance)  
A: Soil biota actor (e.g., bacteria, fungi, nematodes)  
M: Measurement method (e.g., qPCR, Shannon diversity index)  
T: Temporal scope (e.g., timing after treatment)  
I: Locational scope (e.g., soil depth, field site)  
C: Contrasting practice (e.g. no tillage)

3. Relevance Criteria
Mark an abstract as relevant if it includes the following core elements:
L, E, P, A, and ideally C (C can often be implied).
Other fields (M, T, I) are helpful but not required for prescreening.

4. Output Format
Return the result in JSONL format (one valid JSON object on a single line).

The object must contain the following fields:
    - "relevance": 1 if the abstract should proceed to the next stage, 0 if not.
    - "comment": A short explanation (1-2 sentences max).

5. Output Format Requirements
    - Output must be a single-line JSON object.
    - Do not include any additional text, comments, or line breaks.
    - Use double quotes for all keys and string values.
    - Ensure the result is valid JSON (RFC 8259-compliant).

6. Input Abstract    

{abstract}
'''
    result = parse_JSONL(llm.ask(prompt, **kwargs))
    return result


def extract_patterns(llm, text, **kwargs):

    prompt_intro = '''I am interested in how land management practices affect soil biota actors and how this is measured. I want you to analyze the abstract of a scientific publication. I will provide you with a template which you will fill in using the information extracted from the abstract.'''

    prompt_task_description = '''I am looking for specific, compact knowledge patterns which fit the following template:
    
    1. land management practice L
    2. has effect E
    3. on property P
    4. of soil biota actor A
    5. determined by method or measurement M
    6. in temporal scope T
    7. in locational scope I
    8. compared to contrasting land management practice C

For example: 
    1. reduced tillage (L)
    2. increases (E)
    3. diversity (P)
    4. nematodes (A)
    5. Shannon diversity index (M)
    6. seven months after tillage (T)
    7. 0-10 cm soil layers (I)
    9. conventional tillage (C)'''

    prompt_additional_requirements = '''Here are some additional requirements:
    
    - Ignore sentences that express doubt, uncertainty, lack of knowledge, or that only describe the study aim without reporting results.
    - For the effect field, use only one of these options: "increase", "decrease", "no effect", "NA".
    - Make sure to include actors that are enzymes, communities, functional groups (e.g., microbes), or specific taxa.'''

    prompt_export = f'''You will now export the extracted soil biology patterns from the abstract into a structured format for analysis.

1. Task
    - For each extracted pattern, produce a flat JSON object with standardized fields.
    - Each JSON object must represent one complete practice-effect-actor pattern.
    - Apply unification rules and controlled vocabularies as described below.

2. Output Format
Output must follow JSONL (JSON Lines) format:
    - Each line must contain exactly one complete JSON object.
    - Do not wrap the output in an array.
    - Do not use newline-separated key-value pairs inside objects.
    - Do not include any extra text, headers, or commentary.
    - Use double quotes for all strings.
    - If a value is unknown or not applicable, use "NA".

Each JSON object must contain the following fields:

{chr(10).join(pattern_fields_quoted)}

Field-specific requirements:
    - "land_management_practice_category" and "contrasting_land_management_practice_category" must be one of:
    "Carbon and nutrient management", "Vegetation management", "Soil management", "Grazing management", "Pest management", "NA"
    - "location_country" must include the country only.
    - "study_type" must be one of: "field", "greenhouse", or "pot/incubation".
    - "sentences" should contain the sentence(s) from which the pattern was extracted.
    - "comment" may include clarifying notes or "NA" if unused.
    - If no comparator is explicitly stated, assume the contrasting practice is the standard untreated/control condition. In that case, set contrasting_land_management_practice = "Control" or "Untreated", contrasting_land_management_practice_unified = "Control" or "Untreated", and assign contrasting_land_management_practice_category to the same category as the tested practice.

3. Unification Rules
Apply the following terminology in the "*_unified" fields:

Carbon and nutrient management
Biochar, Inorganic fertilizer, Mixed fertilizer, Organic fertilizer, Retaining crop residues, No biochar, No retaining crop residues, Unfertilized, Unfertilized/Inorganic fertilized

Vegetation management
Cover cropping, Crop diversification, Crop rotation, Intercropping, Bare fallow, Monoculture, No crop rotation, Edge crop, No crop diversification

Soil management
Liming, Reduced tillage, Salinization, Conventional tillage, No salinization, No tillage, No liming

Grazing management
Grazing, Ungrazed, Cattle rotation, No cattle rotation

Pest management
Biocides, Bt GMO crop, Herbicides, Nematicides, Plastic film mulch, Non-GMO, Fungicides, Insecticides, Reduced biocide application


Additional normalization
    - Represent "Conservation tillage" as "Reduced tillage".
    - Represent "Agroforestry" as "Crop diversification".
'''

    prompt_split_conjuncts = f'''Review the current list of extracted patterns. Some patterns may contain conjunctions in the property or actor fields.

1. Task
    - If the property or actor field contains conjunctions (e.g., "and", "or", "as well as", "along with"), split them into separate items.
    - If both fields contain conjunctions, generate all possible combinations (Cartesian product).
    - If there are no conjunctions, keep the original pattern unchanged.
    - Keep all other fields exactly the same as in the original pattern.

2. Output Format
    - Output the revised patterns in JSONL format (one valid JSON object per line).
    - Each object must have the same structure and fields as the input.

3. Output Requirements
    - Use double quotes for all strings.
    - If a field is missing or not applicable, it should still be included as "NA".
    - Do not include any extra text, explanations, or formatting outside of the JSON lines.

4. Fields in Each JSON Object

{chr(10).join(pattern_fields_quoted)}'''

    
    _ = llm.ask(prompt_intro, **kwargs)
    _ = llm.ask(prompt_task_description, **kwargs)
    _ = llm.ask(prompt_additional_requirements, **kwargs)
    _ = llm.ask(text, **kwargs)
    patterns = parse_JSONL(llm.ask(prompt_export, **kwargs), pattern_fields)
    result = parse_JSONL(llm.ask(prompt_split_conjuncts, **kwargs), pattern_fields)
    return result


def extract_score(llm, text, **kwargs):
    if llm.reset_for_each_call:
        raise TypeError('LLM must retain context here')
        
    prompt1 = '''I am researching the literature on how land management practices impact soil biota and the methodologies used to measure these effects. My goal is to identify patterns that describe how specific land management practices influence particular soil biota actors compared to contrasting practices. First, I aim to develop a method to evaluate scientific abstracts based on how effectively they describe these patterns, including information on the practices, effects, actors, and contrasts. I will give you scoring instructions which you will apply to the given abstract.

LLM Abstract Scoring Protocol for Soil Biology Data Mining

Objective: To evaluate the clarity, specificity, and completeness of information in scientific abstracts describing the effects of agricultural practices on soil biology. This scoring helps determine the abstract's suitability for automated data extraction.

Starting Score: Every abstract begins with a score of 5 points.

Deduction Rules: Apply the following deductions based on the abstract's content. Deductions are cumulative unless otherwise specified.

1. Comparison Treatment Clarity
	- Evaluate: Whether a comparison/control treatment (e.g., control, baseline, conventional practice, reference, untreated, "contrast") is mentioned and consistently referenced when describing the effects of an agricultural practice.
	- Deduction Rules:
		- (Rule 1.1) Missing Comparison Context (-1 point): If no comparison treatment is mentioned anywhere in the abstract in relation to at least one reported effect of a practice on a biological actor, deduct 1 point overall.
		- (Rule 1.2) Inconsistent Comparison Reference (-0.5 points): If a comparison treatment is mentioned somewhere in the abstract, but at least one sentence describing a specific effect of a practice fails to reference this comparison (implicitly or explicitly), deduct 0.5 points overall. (Apply only if Rule 1.1 does not apply).

2. Treatment Complexity: Combined Practices
	- Evaluate: Whether multiple distinct agricultural practices (e.g., tillage plus organic fertilization, cover crop with reduced irrigation) are applied simultaneously within the same treatment.
	- Deduction Rules:
		- (Rule 2.1) Combined Practices Applied (-0.5 points): If any treatment involves the simultaneous application of multiple distinct agricultural practices, deduct 0.5 points.
		- (Rule 2.2) Effects Not Isolated (-0.5 points): If the experimental design included both combined and individual practice treatments (e.g., Control, Tillage, Fertilizer, Tillage+Fertilizer), but the abstract only reports outcomes for the combined treatment without stating the effects of the individual practices separately, deduct an additional 0.5 points (total -1.0 for Category 2).
	- Exception: If the design exclusively used combined treatments compared to a control (e.g., Control vs. Tillage+Fertilizer, with no separate Tillage or Fertilizer treatments), apply only the initial 0.5-point deduction from Rule 2.1.

3. Treatment Complexity: Multiple Levels/Rates/Types
	- Evaluate: Whether multiple levels, rates, intensities, or types exist for a single category of agricultural practice (e.g., different tillage intensities: conventional vs. reduced vs. no-till; distinct biochar application rates: 0, 5, 10 t/ha; varying fertilization N levels: 0, 60, 120 kg/ha ; various cover crop mixtures: monoculture vs. polyculture).
	- Deduction Rules:
		- (Rule 3.1) Multiple Levels Exist (-0.5 points): If multiple levels, rates, or types are used for any single practice category, deduct 0.5 points.
		- (Rule 3.2) Outcomes Not Linked to Specific Level (-0.5 points): If multiple levels exist (Rule 3.1 applies), and the abstract reports outcomes (effects) without clearly indicating which specific level/rate/type produced each reported outcome, deduct an additional 0.5 points (total -1.0 for Category 3).

4. Contextual Complexity: Sampling Time/Depth/Method
	- Evaluate: Whether results are described from multiple sampling times (e.g., different seasons, years), soil depths (e.g., 0-10 cm vs 10-20 cm), or using different measurement methods for the same biological parameter (e.g., PLFA vs. qPCR for bacterial abundance).
	- Deduction Rules:
		- (Rule 4.1) Multiple Contexts Exist (-0.5 points): If results from multiple distinct times, depths, or methods are presented, deduct 0.5 points.
		- (Rule 4.2) Results Not Distinguished by Context (-0.5 points): If multiple contexts exist (Rule 4.1 applies), and the abstract does not clearly distinguish the results specific to each time, depth, or method (i.e., it's ambiguous when/where/how a result was obtained), deduct an additional 0.5 points (total -1.0 for Category 4).

5. Effect Direction Clarity
	- Evaluate: Whether the abstract clearly and unambiguously states the direction of the effect (increase, decrease, or no effect) of each agricultural practice on the biological actor/property.
	- Deduction Rule:
		- (Rule 5.1) Vague Effect Language (-1 point): If the language used to describe the effect's direction for any key finding remains vague or ambiguous (e.g., "moderately impacted," "affected," "influenced," "responded differently," "showed changes," "altered," "appeared to benefit/suffer"), deduct 1 point. (Look for explicit terms like: increased, decreased, enhanced, reduced, stimulated, inhibited, higher, lower, no effect, no significant difference, similar to control).

6. Effect Reporting Style: Numeric vs. Descriptive
	- Evaluate: Whether the effect (increase, decrease, no effect) of the practice is reported only in numeric terms (e.g., absolute values, percentages, ratios) without an accompanying descriptive statement of the direction.
	- Deduction Rule:
		- (Rule 6.1) Numeric-Only Reporting (-0.5 points): If any key effect is reported only using numbers or percentages without a corresponding descriptive word (e.g., "increased," "decreased," "higher," "lower"), deduct 0.5 points. (Having both numeric values and a descriptive word is acceptable and not penalized).

7. Measured Property Clarity
	- Evaluate: Whether the abstract explicitly states which specific biological property (parameter) is being affected by the agricultural practice.
	- Deduction Rule:
		- (Rule 7.1) Unspecified Property (-0.5 points): If the specific property being measured or affected is not clearly stated for any key result involving a biological actor (e.g., the abstract just says "affected microbes" without specifying abundance, diversity, activity, etc.), deduct 0.5 points. (Look for terms like: abundance, biomass, richness, diversity [Shannon, Simpson], evenness, community composition, activity [enzyme names, respiration], gene copy number, population size, presence/absence).

8. Explicit Results Linkage
	- Evaluate: Whether the abstract presents explicit results directly linking a specific agricultural practice to a specific effect on a specific biological actor/property, rather than making general or vague claims about the study's findings or hypotheses.
	- Deduction Rule:
		- (Rule 8.1) Vague Link / Missing Specifics (-2 points): If the abstract only includes vague statements (e.g., "the hypothesis was proven," "results supported the benefits of the practice," "microbial communities were influenced") without explicitly stating which practice led to what effect (increase/decrease/no effect) on which specific biological actor or property for its main conclusions, deduct 2 points.

Final Scoring Instructions & Interpretation:

1.	Cumulative Application: All deduction rules are cumulative. Starting from the initial score of 5, apply every deduction for which the condition is met within the abstract. The final score is calculated as 5 minus the sum of all applied deductions. If the final score is negative it is set to 0.

2.	Focus on Result Sentences: The primary focus for applying these rules is the set of sentences identified by the LLM as containing the core results linking agricultural practices to biological effects (these are the sentences typically provided in an "extracted sentences" or "result sentences" output column).

3.	Use Full Abstract for Context: While focusing on the result sentences, consult the entire abstract text as needed to determine if contextual information (like the identity of a comparison treatment, details about combined practices, or levels/rates) exists elsewhere in the abstract.
		- Example: If a result sentence states "Tillage increased bacterial abundance," check the rest of the abstract to see if a comparison (e.g., "compared to no-till") is mentioned anywhere. If it is mentioned somewhere, apply Rule 1.2 (-0.5) because it's missing from the result sentence. If it's mentioned nowhere in the entire abstract, apply Rule 1.1 (-1.0).

4.	Goal - Predict Extraction Consistency: The final score is not a judgment of the abstract's overall scientific quality. Instead, it measures the clarity, specificity, and completeness of the information presented for the purpose of data extraction. A lower score indicates higher ambiguity or missing information pertinent to the extraction task, predicting greater potential variance between automated LLM extraction and human interpretation/extraction. Abstracts scoring higher are expected to yield more consistent and reliable data extraction results.

In essence for the LLM: Evaluate the abstract based on all the rules. Concentrate your evaluation on the key result sentences you identified, but use the full abstract text to find necessary context before applying deductions. Apply deductions cumulatively. The score reflects how easy/unambiguous it is to extract the specific practice-effect-actor information from this abstract.'''
    _ = llm.ask(prompt1, **kwargs) #, seed=SEED, temperature=TEMPERATURE)

    prompt2 = f'''Evaluate the following abstract using the LLM Abstract Scoring Protocol for Soil Biology Data Mining provided earlier.

1. Task
    - Start with a score of 5 points.
    - Apply all deduction rules as specified in the protocol.
    - If the total deductions result in a negative value, set the final score to 0.

2. Output Format
Return the result in JSONL format (one valid JSON object on a single line).

The object must contain:
    - "score": A number between 0 and 5 representing the final score.
    - "score_explanation": A concise explanation (1–2 sentences) justifying the score, ideally referencing deduction categories or rules.

3. Output Requirements
    - Output must be a single-line JSON object.
    - Do not include any additional text, comments, or line breaks.
    - Use double quotes for all keys and string values.
    - Ensure the result is valid JSON (RFC 8259-compliant).

4. Input Abstract

{text}
'''
    answer = llm.ask(prompt2, **kwargs)
    return parse_JSONL(answer, required_fields=['score', 'score_explanation'])


def unify_actors(llm, actor_sentence_dicts, unified_actors_list, **kwargs):
    prompt = f'''Map soil biota actors to standardized names using the following guidelines:

1. Input Format
    - "Extracted items": A Python-style list of dictionaries, where each dictionary has the keys:
        - "actor": the extracted actor string
        - "sentence": the full sentence from which the actor was extracted
    - "Unified categories": A Python-style list of standardized soil biota categories.

2. Task
    - For each item in "Extracted items", identify the closest matching category from "Unified categories" using generalization, common sense, and the sentence context of the actor.
    - If the actor refers to an enzyme, always unify as "Soil microbiome".
    - If no suitable match exists, assign "NA".

3. Output
Return the result in JSONL format. For each item, output one line as a valid JSON object with the following fields:
    - "actor": the original extracted name
    - "actor_unified": the standardized matched category from the unified list, or "NA"

4. Output Format Requirements
    - Do not include any extra text, explanation, or commentary.
    - Output only one valid JSON object per line (JSONL format).
    - The JSON must use double quotes for all strings.

5. Input Data

Extracted items: {actor_sentence_dicts}

Unified categories: {unified_actors_list}
'''
    
    answer = llm.ask(prompt, **kwargs)
    return parse_JSONL(answer, required_fields=['actor', 'actor_unified'])


def unify_property(llm, property_sentence_dicts, unified_property_list, **kwargs):
    prompt = f'''Unify the names of soil biota properties that were reported to be affected by land management practices in scientific publications.

1. Input Format
    - "Extracted items": A Python-style list of dictionaries, where each dictionary has the keys:
        - "property": the extracted property name
        - "sentence": the full sentence from which the property was extracted
    - "Unified categories": A Python-style reference list of standardized property names used for unification.

2. Task
    - For each item in "Extracted items", find the most appropriate match from "Unified categories" using generalization, common sense, and the sentence context of the property.
    - If no suitable match exists, assign "NA" as the property_unified value.

3. Output
Return the result in JSONL format, with one valid JSON object per line. Each object must include:
    - "property": the original property name
    - "property_unified": the standardized match from the reference list, or "NA"

4. Output Format Requirements
    - Output only one valid JSON object per line (JSONL format).
    - Use double quotes for all string values.
    - Do not include any headers, explanations, or additional text.

5. Input Data

Extracted items: {property_sentence_dicts}

Unified categories: {unified_property_list}
'''
    answer = llm.ask(prompt, **kwargs)
    return parse_JSONL(answer, required_fields=['property', 'property_unified'])



    
