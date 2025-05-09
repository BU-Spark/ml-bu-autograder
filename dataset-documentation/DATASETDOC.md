***Dataset Information***

* What data sets did you use in your project? Please provide a link to the data sets, this could be a link to a folder in your GitHub Repo, Spark\! owned Google Drive Folder for this project, or a path on the SCC, etc.
https://drive.google.com/drive/u/1/folders/1m8UJIyY62FGBK7n7ZNMAlvGPI_hzceny

* Please provide a link to any data dictionaries for the datasets in this project. If one does not exist, please create a data dictionary for the datasets used in this project. **(Example of data dictionary)**   

* What keywords or tags would you attach to the data set?  
  * Domain(s) of Application: Computer Vision, OCR, Image Classification, NLP, Topic Modeling, Text Classification, Summarization  
  * Tags: Tech, Education

*The following questions pertain to the datasets you used in your project.*   
*Motivation* 

* For what purpose was the dataset created? Was there a specific task in mind? Was there a specific gap that needed to be filled? Please provide a description. 
This dataset is just student submissions and grades from previous semester.

*Composition*

* What do the instances that comprise the dataset represent (e.g., documents, photos, people, countries)? Are there multiple types of instances (e.g., movies, users, and ratings; people and interactions between them; nodes and edges)? What is the format of the instances (e.g., image data, text data, tabular data, audio data, video data, time series, graph data, geospatial data, multimodal (please specify), etc.)? Please provide a description.   
PDFs, Powerpoints, Excel Sheets, Docs
* How many instances are there in total (of each type, if appropriate)?  

* Does the dataset contain all possible instances or is it a sample (not necessarily random) of instances from a larger set? If the dataset is a sample, then what is the larger set? Is the sample representative of the larger set? If so, please describe how this representativeness was validated/verified. If it is not representative of the larger set, please describe why not (e.g., to cover a more diverse range of instances, because instances were withheld or unavailable).  
It's a sample of all questions that we need AI grading for (i.e. not multiple choice) from past few semesters.

* What data does each instance consist of? “Raw” data (e.g., unprocessed text or images) or features? In either case, please provide a description.   
Raw unprocessed student responses, grader grading, and course material.

* Is there any information missing from individual instances? If so, please provide a description, explaining why this information is missing (e.g., because it was unavailable). This does not include intentionally removed information, but might include redacted text.   
N/A.

* Are there recommended data splits (e.g., training, development/validation, testing)? If so, please provide a description of these splits, explaining the rationale behind them  
N/A

* Are there any errors, sources of noise, or redundancies in the dataset? If so, please provide a description.  
N/A

* Is the dataset self-contained, or does it link to or otherwise rely on external resources (e.g., websites, tweets, other datasets)? If it links to or relies on external resources,   
  * Are there guarantees that they will exist, and remain constant, over time;  
  * Are there official archival versions of the complete dataset (i.e., including the external resources as they existed at the time the dataset was created)?  
  * Are there any restrictions (e.g., licenses, fees) associated with any of the external resources that might apply to a dataset consumer? Please provide descriptions of all external resources and any restrictions associated with them, as well as links or other access points as appropriate.   

N/A: dataset is self contained.

* Does the dataset contain data that might be considered confidential (e.g., data that is protected by legal privilege or by doctor-patient confidentiality, data that includes the content of individuals’ non-public communications)? If so, please provide a description.   
No. All student data was de-anonymized.

* Does the dataset contain data that, if viewed directly, might be offensive, insulting, threatening, or might otherwise cause anxiety? If so, please describe why.   
No.

* Is it possible to identify individuals (i.e., one or more natural persons), either directly or indirectly (i.e., in combination with other data) from the dataset? If so, please describe how.   
No, not easily.

* Dataset Snapshot, if there are multiple datasets please include multiple tables for each dataset. 


| Size of dataset |  |
| :---- | :---- |
| Number of instances |  |
| Number of fields  |  |
| Labeled classes |  |
| Number of labels  |  |


  
*Collection Process*

* What mechanisms or procedures were used to collect the data (e.g., API, artificially generated, crowdsourced \- paid, crowdsourced \- volunteer, scraped or crawled, survey, forms, or polls, taken from other existing datasets, provided by the client, etc)? How were these mechanisms or procedures validated?  
Naturally generated through the course of the semester.

* If the dataset is a sample from a larger set, what was the sampling strategy (e.g., deterministic, probabilistic with specific sampling probabilities)?  
N/A
* 
* Over what timeframe was the data collected? Does this timeframe match the creation timeframe of the data associated with the instances (e.g., recent crawl of old news articles)? If not, please describe the timeframe in which the data associated with the instances was created. 
Spring/Fall 2024 semesters

*Preprocessing/cleaning/labeling* 

* Was any preprocessing/cleaning/labeling of the data done (e.g., discretization or bucketing, tokenization, part-of-speech tagging, SIFT feature extraction, removal of instances, processing of missing values)? If so, please provide a description. If not, you may skip the remaining questions in this section.   
No.

* Were any transformations applied to the data (e.g., cleaning mismatched values, cleaning missing values, converting data types, data aggregation, dimensionality reduction, joining input sources, redaction or anonymization, etc.)? If so, please provide a description.   
No.

* Was the “raw” data saved in addition to the preprocessed/cleaned/labeled data (e.g., to support unanticipated future uses)? If so, please provide a link or other access point to the “raw” data, this could be a link to a folder in your GitHub Repo, Spark\! owned Google Drive Folder for this project, or a path on the SCC, etc.  
No.

* Is the code that was used to preprocess/clean the data available? If so, please provide a link to it (e.g., EDA notebook/EDA script in the GitHub repository). 
Yes, the code to process PDFs and other formats is in [bytes_to_doc_util.py](../app/utils/bytes_to_doc_util.py).

*Uses* 

* What tasks has the dataset been used for so far? Please provide a description. 
Validating grading accuracy on test samples, ensuring we can process data of this format.

* What (other) tasks could the dataset be used for?  
Providing examples to LLM for sample solutions and grades.

* Is there anything about the composition of the dataset or the way it was collected and preprocessed/cleaned/labeled that might impact future uses?   
Its multimodal.

* Are there tasks for which the dataset should not be used? If so, please provide a description.
N/A

*Distribution*

* Based on discussions with the client, what access type should this dataset be given (eg., Internal (Restricted), External Open Access, Other)?
Internal

*Maintenance* 

* If others want to extend/augment/build on/contribute to the dataset, is there a mechanism for them to do so? If so, please provide a description. 
N/A

*Other*

* Is there any other additional information that you would like to provide that has not already been covered in other sections?
N/A