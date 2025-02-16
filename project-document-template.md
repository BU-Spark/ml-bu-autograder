# Technical Project Document Template

## *Josh Yip, Zach Gentile, Aseef Mohammad, Fahim Uddin, 2025-February-15 vx.x.x-dev*

## Overview

_The AI-Assisted Grading Tool for Written Answers and Complex Assignments is a project for Boston University’s Metropolitan College Office of Education Technology and Innovation (MET ETI). The tool aims to refine and optimize AI-assisted grading capabilities for CS 581 quizzes and assignments using Azure AI Studio, GPT-4o, and Retrieval-Augmented Generation (RAG). The main challenges include grading consistency, accuracy, and alignment with instructor expectations. The AI model will need to evaluate student responses, process supplemental course material, and support file-based grading._

### A. Provide a solution in terms of human actions to confirm if the task is within the scope of automation through AI.

*Current Process:*

A CS 581 student submits a quiz or assignment in Blackboard.

The instructor or TA manually grades the response by referencing rubrics and sample correct answers.

The graded response is entered into Blackboard.

A review is conducted for consistency across multiple graders.

*AI-Assisted Process:*

A student submits a quiz or assignment.

The response is sent via API to an AI model.

The AI grades the response using predefined rubrics, sample answers, and supplemental course material.

The AI returns a structured response including a score and explanation.

The instructor reviews and confirms the AI’s evaluation before finalizing the grade in Blackboard.

AI-graded responses are logged for consistency analysis.

### B. Problem Statement:

*The problem at hand is improving the consistency, accuracy, and reliability of AI-assisted grading for short-answer quizzes and file-based assignments. The AI model must extract a clear score and justification while referencing structured supplemental data, rubrics, and student-uploaded files. The solution should also support file processing, external links, and potential web browsing capabilities for retrieving relevant material.*

### C. Checklist for project completion

*Provide a bulleted list to the best of your current understanding, of the concrete techinal goals and artifacts that, when complete, define the completion of the project. This checklist will likely evolve as your project progresses.*

1. The optimal AI platform for ETI's use case, with documentation on how to access the environment we have set up using this platform, as well as how to use its API.

2. The optimal AI model for ETI's use case, with documentation on how to use the model and its API.

3. The optimal method of adding course material and data for ETI's use case and detailed documentation on how to do this.

4. A set of clear and relevant metric summaries on how we improved performance of AI autograding on CS 581's quiz and assignment data.

### D. Outline a path to operationalization.

*Data Science Projects should have an operationalized end point in mind from the onset. Briefly describe how you see the tool produced by this project being used by the end user beyond a jupyter notebook or proof of concept. If possible, be specific and call out the relevant technologies that will be useful when making this available to the stakeholders as a final deliverable.*

The problem at hand is improving the consistency, accuracy, and reliability of AI-assisted grading for short-answer quizzes and file-based assignments. The AI model must extract a clear score and justification while referencing structured supplemental data, rubrics, and student-uploaded files. The solution should also support file processing, external links, and potential web browsing capabilities for retrieving relevant material.

## Resources

### Data Sets

- Student responses from CS 581 quizzes and assignments

- Instructor-provided rubrics and sample answers

- Supplementary course material (PDFs, slides, videos)



### References

- MET ETI AI-Assisted Grading Requirements Document

- Azure AI Studio Documentation

- GPT-4o, Claude, and LLaMA API Documentation

## Weekly Meeting Updates

*Keep track of ongoing meetings in the Project Description document prepared by Spark staff for your project.*
