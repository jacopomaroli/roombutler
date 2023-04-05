# room-butler

# default params
num_trees: 10
max_depth: 7

# create env
conda create -n decisionTree -c conda-forge tensorflow
CALL conda.bat activate decisionTree

# run tests
you'll need to train a model and populate the .env file first
`make prepare-dev`
`make test`
