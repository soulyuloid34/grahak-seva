# Data report

## Files

- train: 18810 rows | validation: 4031 rows
- columns (train): ['flags', 'instruction', 'category', 'intent', 'response']
- columns (validation): ['flags', 'instruction', 'category', 'intent', 'response']

## Missing values

- train: {'flags': 0, 'instruction': 0, 'category': 0, 'intent': 0, 'response': 0}
- validation: {'flags': 0, 'instruction': 0, 'category': 0, 'intent': 0, 'response': 0}

## Labels

- distinct category in train: 11, in validation: 11
- distinct intent in train: 27, in validation: 27
- intents in validation but not in train: none
- categories in validation but not in train: none
- intents mapped to more than one category: none (clean intent -> category map)

## Class balance

### intent (train)

Largest class 700, smallest 665, imbalance ratio 1.05.

Top 5:

| label | count | share |
|---|---|---|
| switch_account | 700 | 3.7% |
| contact_customer_service | 700 | 3.7% |
| edit_account | 700 | 3.7% |
| check_invoice | 700 | 3.7% |
| complaint | 700 | 3.7% |

Bottom 5:

| label | count | share |
|---|---|---|
| check_cancellation_fee | 665 | 19.4% |
| change_shipping_address | 681 | 19.8% |
| recover_password | 696 | 20.3% |
| delete_account | 696 | 20.3% |
| delivery_options | 697 | 20.3% |

### category (train)

Largest class 4189, smallest 665, imbalance ratio 6.30.

Top 5:

| label | count | share |
|---|---|---|
| ACCOUNT | 4189 | 22.3% |
| ORDER | 2793 | 14.8% |
| REFUND | 2095 | 11.1% |
| CONTACT | 1399 | 7.4% |
| INVOICE | 1399 | 7.4% |

Bottom 5:

| label | count | share |
|---|---|---|
| CANCEL | 665 | 12.0% |
| SUBSCRIPTION | 699 | 12.6% |
| SHIPPING | 1379 | 24.9% |
| DELIVERY | 1396 | 25.2% |
| FEEDBACK | 1398 | 25.2% |

Validation intent counts (top 5):

| label | count | share |
|---|---|---|
| contact_human_agent | 150 | 3.7% |
| delivery_period | 150 | 3.7% |
| complaint | 150 | 3.7% |
| set_up_shipping_address | 150 | 3.7% |
| switch_account | 150 | 3.7% |

## Variation flags

Each flag letter marks a linguistic or style variation of the query (for example politeness, colloquial wording, noise or typos).

- train: {'B': 18810, 'L': 16866, 'Q': 6258, 'I': 5435, 'Z': 3689, 'M': 3467, 'C': 1876, 'K': 1548, 'E': 1352, 'P': 913, 'W': 912, 'N': 324, 'S': 291, 'V': 52}
- validation: {'B': 4031, 'L': 3606, 'Q': 1389, 'I': 1188, 'Z': 800, 'M': 727, 'C': 367, 'K': 360, 'E': 266, 'W': 194, 'P': 191, 'N': 67, 'S': 65, 'V': 16}

## Duplicates and leakage

- duplicate instructions inside train (normalised): 1513
- instructions with conflicting intent labels in train: 0
- exact instructions shared by train and validation: 368
- shared after lowercasing/whitespace normalisation: 423
- share of validation rows affected: 13.10%

## Response notes

- share of train responses containing {{Placeholder}} tokens: 48.3%
- mean response length (words): 105

## Split used

The organizer-provided `train.csv` and `validation.csv` are used exactly as given; no rows are moved between them.

- **Train** is used to fit the intent model and as the retrieval pool for supporting examples.
- **Validation** is held out: it is never used for training, retrieval, threshold tuning or prompt examples. It is used only to report intent Macro-F1, category accuracy and sample outputs.
- The split is therefore reproducible by construction. Any sampling done later (for example 200 validation queries) uses a fixed random seed of 42.
- Caveat: 423 normalised instructions appear in both files, so scores may be slightly optimistic.