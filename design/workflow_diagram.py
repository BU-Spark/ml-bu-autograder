import graphviz
# Correcting the diagram based on the requested changes

# Create new Digraph object
dot = graphviz.Digraph(format='png', engine='dot')
dot.attr(rankdir='TB')

# Nodes
dot.node('IN', 'IN', shape='ellipse', style='filled', fillcolor='lightblue')
dot.node('Router', 'Router', shape='box', style='filled', fillcolor='lightgray')
dot.node('FeatureExtraction', 'Feature Extraction\n(Web-scraping, Doc-\nument Intelligence,\n etc...)', shape='box')
dot.node('Powerpoint', 'Powerpoint', shape='box')
dot.node('PDF', 'PDF', shape='box')
dot.node('HTML', 'Web page (HTML)', shape='box')
dot.node('Video', 'Video', shape='box', style='filled', fillcolor='lightgray')
dot.node('Frames', 'Frames', shape='box')
dot.node('Audio', 'Audio', shape='box', style='filled', fillcolor='lightgray')
dot.node('Images', 'Images', shape='box', style='filled', fillcolor='lightgray')
dot.node('VisionAPI', 'Vision API', shape='ellipse', style='filled', fillcolor='lightyellow')
dot.node('AudioAPI', 'Audio API', shape='ellipse', style='filled', fillcolor='lightyellow')
dot.node('Text', 'Text', shape='box', style='filled', fillcolor='lightgray')
dot.node('AssignmentQuestions', 'Assignment Questions', shape='box')
dot.node('Rubric', 'Rubric', shape='box')
dot.node('LLMAPI', 'LLM API', shape='ellipse', style='filled', fillcolor='lightpink')
dot.node('RAG', 'RAG', shape='ellipse', style='filled', fillcolor='lightgreen')
dot.node('GradedAssignments', 'Graded Assignments w/ Feedback', shape='box')
dot.node('Postgres', '(Postgres)\n- Vector Store\n- State Store', shape='cylinder', style='filled', fillcolor='orange')
dot.node('OUT', 'OUT', shape='ellipse', style='filled', fillcolor='lightblue')

# Edges
dot.edge('IN', 'Router')
dot.edge('Router', 'Powerpoint')
dot.edge('Router', 'PDF')
dot.edge('Router', 'HTML')
dot.edge('Router', 'Video')
dot.edge('Router', 'Audio')
dot.edge('Router', 'Images')
dot.edge('Router', 'Text')

# PowerPoint, PDF, and Web Page go to Feature Extraction
dot.edge('Powerpoint', 'FeatureExtraction')
dot.edge('PDF', 'FeatureExtraction')
dot.edge('HTML', 'FeatureExtraction')

# Feature Extraction routes results into Video, Images, Audio, and Text
dot.edge('FeatureExtraction', 'Video')
dot.edge('FeatureExtraction', 'Audio')
dot.edge('FeatureExtraction', 'Images')
dot.edge('FeatureExtraction', 'Text')

# Normal Processing Path
dot.edge('Video', 'Frames')
dot.edge('Video', 'Audio')
dot.edge('Frames', 'VisionAPI', label='At some sample rate')
dot.edge('Audio', 'AudioAPI')
dot.edge('Images', 'VisionAPI')

# APIs processing
dot.edge('VisionAPI', 'Text')
dot.edge('AudioAPI', 'Text')

# Text processing for assignments
dot.edge('AssignmentQuestions', 'Text', color='red')
dot.edge('Rubric', 'Text', color='red')

# Text goes into Vector Store for RAG and LLM API
dot.edge('Text', 'Postgres', label='If is course material\nsaved structured text\nto vector store', color='blue')
dot.edge('Postgres', 'RAG', color='red')
dot.edge('Text', 'LLMAPI', label='If student response, \ncombine w/ Rubric\n+ Assignment Prompt', color='red')
dot.edge('RAG', 'LLMAPI', color='red')

# Grading and results storage
dot.edge('LLMAPI', 'GradedAssignments', color='red')
dot.edge('GradedAssignments', 'Postgres', label='Results saved', color='red')
dot.edge('Postgres', 'OUT')

# Render the graph
graph_path = "ai_autograder_workflow_corrected"
dot.render(graph_path)