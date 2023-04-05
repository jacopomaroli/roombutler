import pandas as pd
import pytest
import numpy as np
from scipy.stats import randint
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, precision_score, recall_score, ConfusionMatrixDisplay
from sklearn.tree import export_graphviz
from sklearn.model_selection import RandomizedSearchCV, train_test_split

# Read data and normalize fields
bank_data = pd.read_csv("test/assets/bank-marketing.csv", sep=";")
bank_data = bank_data.loc[:, ['age', 'default',
                              'cons.price.idx', 'cons.conf.idx', 'y']]
bank_data['default'] = bank_data['default'].map(
    {'no': 0, 'yes': 1, 'unknown': 0})
bank_data['y'] = bank_data['y'].map({'no': 0, 'yes': 1})

# Split the data into features (X) and target (y)
X = bank_data.drop('y', axis=1)
y = bank_data['y']

# Split the data into training and test sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)


def test_estimator_fixed_params():
    rf = RandomForestClassifier(n_estimators=10, max_depth=7)
    rf.fit(X_train, y_train)

    y_pred = rf.predict(X_test)

    # Create the confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    # ConfusionMatrixDisplay(confusion_matrix=cm).plot();

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)

    print("Accuracy:", accuracy)
    print("Precision:", precision)
    print("Recall:", recall)

    assert accuracy > 0.8, "Low accuracy"


@pytest.mark.skip(reason="quite long execution")
def test_estimator_optimizing_params():
    param_dist = {'n_estimators': randint(50, 500),
                  'max_depth': randint(1, 20)}

    # Create a random forest classifier
    rf = RandomForestClassifier()

    # Use random search to find the best hyperparameters
    rand_search = RandomizedSearchCV(
        rf, param_distributions=param_dist, n_iter=5, cv=5)

    # Fit the random search object to the data
    rand_search.fit(X_train, y_train)

    best_rf = rand_search.best_estimator_

    # Print the best hyperparameters
    print('Best hyperparameters:',  rand_search.best_params_)

    # Generate predictions with the best model
    y_pred = best_rf.predict(X_test)

    # Create the confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    # ConfusionMatrixDisplay(confusion_matrix=cm).plot();

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)

    print("Accuracy:", accuracy)
    print("Precision:", precision)
    print("Recall:", recall)

    # Create a series contain feature importances from the model and feature names from the training data
    feature_importances = pd.Series(
        best_rf.feature_importances_, index=X_train.columns).sort_values(ascending=False)

    # Plot a simple bar chart
    # feature_importances.plot.bar();

    assert accuracy > 0.8, "Low accuracy"
