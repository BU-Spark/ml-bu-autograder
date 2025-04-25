TODO: rn there are only 5 bullets but they can probably be split further

1. (Josh) Technical recommendations for optimal tools for MET's use case. The implications of this as I understanding is you are looking for something that is primary within the Azure ecosystem and if outside the Azure ecosystem, it should be something that should be integrable easily.
- tell them about Azure's offerings for pdf extract, ocr, etc
- more stuff
- cohere and how that can be integrated?

2. (Fahim) Recommendations for the optimal model (or combination of) in that tool for MET's use case.
- Maybe tell them they can use a mixture and best model depends on use case.
- use gpt 4.1 nano for content thats directly written in the course material (no reasoning needed) - pure summarization.
- gpt 4.1 mini for most general purpose tasks.
- gpt 4.1 for anything involving formal reasoning BUT the problem is widely known/well understood.
- for more complex formal math tasks a reasoning model (gemini 2.5 pro) is needed. expensive.

3. (Zach) Recommendations on optimal configurations for that model (temperature, etc) and as well as how to specify these configs.


4. (Aseef) Recommendations on an optimal way of hosting course material, extract information from it (vectorizing) and referencing that for RAG in a way that is compatible with the Azure ecosystem.
- here we can talk about our custom grading pipelines and how that might be integrated in azure.

5. (Zach) Prompt engineering methods and techniques applicable to your use case.
- idk