"""
 Classes and function for answering analogy questions
"""

import logging
from collections import OrderedDict
import six
from six.moves import range
import scipy
import pandas as pd
from itertools import product

logger = logging.getLogger(__name__)
import sklearn
from .datasets.analogy import *
from .utils import batched
from web.embedding import Embedding

class SimpleAnalogySolver(sklearn.base.BaseEstimator):
    """Answer analogy questions"""

    def __init__(self, w, method="add", batch_size=300, k=None):
        self.w = w
        self.batch_size = batch_size
        self.method = method
        self.k = k

    def score(self, X, y):
        """Calculate accuracy on analogy questions dataset

        Args:
          X(array-like): Analogy questions.
          y(array-like): Analogy answers.

        Returns:

        """
        return np.mean(y == self.predict(X))

    def predict(self, X):
        """Answer analogy questions

        Args:
          X(array-like): Analogy questions.

        Returns:

        """
        w = self.w.most_frequent(self.k) if self.k else self.w
        words = self.w.vocabulary.words
        word_id = self.w.vocabulary.word_id
        mean_vector = np.mean(w.vectors, axis=0)
        output = []

        missing_words = 0
        for query in X:
            for query_word in query:
                if query_word not in word_id:
                    missing_words += 1
        if missing_words > 0:
            logger.warning("Missing {} words. Will replace them with mean vector".format(missing_words))

        # Batch due to memory constaints (in dot operation)
        for id_batch, batch in enumerate(batched(range(len(X)), self.batch_size)):
            ids = list(batch)
            X_b = X[ids]
            if id_batch % np.floor(len(X) / (10. * self.batch_size)) == 0:
                logger.info("Processing {}/{} batch".format(int(np.ceil(ids[1] / float(self.batch_size))),
                                                            int(np.ceil(X.shape[0] / float(self.batch_size)))))

            A, B, C = np.vstack(list(w.get(word, mean_vector) for word in X_b[:, 0])), \
                      np.vstack(list(w.get(word, mean_vector) for word in X_b[:, 1])), \
                      np.vstack(list(w.get(word, mean_vector) for word in X_b[:, 2]))

            if self.method == "add":
                D = np.dot(w.vectors, (B - A + C).T)
            elif self.method == "mul":
                D_A = np.log((1.0 + np.dot(w.vectors, A.T)) / 2.0 + 1e-5)
                D_B = np.log((1.0 + np.dot(w.vectors, B.T)) / 2.0 + 1e-5)
                D_C = np.log((1.0 + np.dot(w.vectors, C.T)) / 2.0 + 1e-5)
                D = D_B - D_A + D_C
            else:
                raise RuntimeError("Unrecognized method parameter")

            # Remove words that were originally in the query
            for id, row in enumerate(X_b):
                D[[w.vocabulary.word_id[r] for r in row if r in
                   w.vocabulary.word_id], id] = np.finfo(np.float32).min

            output.append([words[id] for id in D.argmax(axis=0)])

        return np.array([item for sublist in output for item in sublist])