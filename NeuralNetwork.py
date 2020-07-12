"""
Don't take this class seriously, first, I have to learn how to use neural networks,
because I have no clue about machine learning :)
"""


from datetime import datetime

import arrow as arrow
import numpy as np
import sys

from Common import readResponseTimesFromLogFile


def activation_function(x):
    return sigmoid(x)


def activation_function_derivative(x):
    return sigmoid_derivative(x)


def sigmoid(x):
    return 1/(1 + np.exp(-x))


def sigmoid_derivative(x):
    #computing derivative to the Sigmoid function
    return x * (1 - x)


def sigmoid_derivative2(x):
    return sigmoid(x) * (1-sigmoid(x))


class NeuralNetwork:
    def __init__(self, x: np.ndarray, y: np.ndarray):
        # seeding for random number generation
        np.random.seed(1)

        self.input      = x
        print("Input: {}".format(self.input.shape))
        #self.weights1   = np.random.rand(self.input.shape[1], self.input.shape[0])
        self.weights1   = np.full((self.input.shape[1], self.input.shape[0]), 1.0)
        print("W1 shape: {}".format(self.weights1.shape))
        self.weights2   = np.random.rand(self.input.shape[0], 1)
        print("W2 shape: {}".format(self.weights2.shape))
        self.y          = y
        print("Y shape: {}".format(self.y.shape))
        self.output     = np.zeros(self.y.shape)

    def feedforward(self):
        print("Input * W1 = {}".format(np.dot(self.input, self.weights1)))
        self.layer1 = activation_function(np.dot(self.input, self.weights1))
        print("L1: {}".format(self.layer1))
        self.output = activation_function(np.dot(self.layer1, self.weights2))
        print("Output: {}".format(self.output.shape))

    def backprop(self):
        # application of the chain rule to find derivative of the loss function with respect to weights2 and weights1
        d_weights2 = np.dot(self.layer1.T, (2*(self.y - self.output) * activation_function_derivative(self.output)))
        d_weights1 = np.dot(self.input.T,  (np.dot(2*(self.y - self.output) * activation_function_derivative(self.output), self.weights2.T) * activation_function_derivative(self.layer1)))

        # update the weights with the derivative (slope) of the loss function
        self.weights1 += d_weights1
        self.weights2 += d_weights2


def read_training_data(path):
    response_times = readResponseTimesFromLogFile(path)

    timestamps = [*response_times]
    responsetimes = [*response_times.values()]

    return timestamps, responsetimes


max_response_time = 0.0


def transform_training_data(timestamps, response_times):
    #unix_timestamps = map(lambda t: arrow.get(t).timestamp, timestamps)
    unix_timestamps = map(lambda t: t.timestamp(), timestamps)

    global max_response_time
    max_response_time = max(response_times)

    print("max response time: {}".format(max_response_time))

    normalized_response_times = map(lambda r: r / max_response_time, response_times)

    x = np.array([list(unix_timestamps)]).T
    y = np.array([list(normalized_response_times)]).T

    print(x)
    print(y)

    return x, y


if __name__ == "__main__":

    timestamps, response_times = read_training_data("ARS_Times/Test.log")
    x1, y1 = transform_training_data(timestamps, response_times)

    n = NeuralNetwork(x1, y1)

    n.feedforward()

    print(n.output)
    print(n.output*max_response_time)

    # for i in range(10):
    #     n.feedforward()
    #     n.backprop()
    #
    # n.feedforward()
    # print(n.output*max_response_time)

    # y = np.array([[0, 1, 1, 0]]).T
    #
    # x = np.array([[0, 0, 1], [0, 1, 1], [1, 0, 1], [1, 1, 1]])
    #
    # n = NeuralNetwork(x, y)
    #
    # n.feedforward()
    #
    # print(n.output)
    #
    # for i in range(1500):
    #     n.feedforward()
    #     n.backprop()
    #
    # n.feedforward()
    # print(n.output)
    #
    # n.input = np.array([[0, 1, 0], [1, 1, 0]])
    # n.feedforward()
    # print(n.output)
