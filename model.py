import csv
import cv2
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import bernoulli
import scipy.misc
import math
from sklearn.utils import shuffle
import matplotlib.image as mpimg
import errno
import json
import os
from keras.models import Sequential
from keras.layers import Flatten, Dense, Lambda, Activation, Cropping2D, Dropout
from keras.layers.convolutional import Convolution2D
from keras.layers.pooling import MaxPooling2D
from keras.optimizers import Adam
from random import sample


def path(source_path):
    filename = source_path.split('\\')[-1]
    current_path = data_path + 'IMG/' + filename
    return current_path


def random_flip(image, steering_angle, flipping_prob=0.5):
    head = bernoulli.rvs(flipping_prob)
    if head:
        return np.fliplr(image), -1 * steering_angle
    else:
        return image, steering_angle


def crop_img(image):
    top = 70
    bottom = image.shape[0] - 25
    return image[top:bottom, :]


def shadow(image):
    img = np.copy(image)
    h, w = image.shape[0], image.shape[1]
    [x1, x2] = np.random.choice(w, 2, replace=False)
    k = h / (x2 - x1)
    b = - k * x1
    for i in range(h):
        c = int((i - b) / k)
        img[i, :c, :] = (image[i, :c, :] * .5).astype(np.int32)
    return img


def random_gamma(image):
    """
    Random gamma correction is used as an alternative method changing the brightness of
    training images.
    http://www.pyimagesearch.com/2015/10/05/opencv-gamma-correction/
    :param image:
        Source image
    :return:
        New image generated by applying gamma correction to the source image
    """
    gamma = np.random.uniform(0.4, 1.5)
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255
                      for i in np.arange(0, 256)]).astype("uint8")

    # apply gamma correction using the lookup table
    return cv2.LUT(image, table)


def blur(img):
    gb = cv2.GaussianBlur(img, (5,5), 20.0)
    return cv2.addWeighted(img, 2, gb, -1, 0)


def resize(image, new_size):
    return scipy.misc.imresize(image, new_size)


def process_img(image, steering_angle):
    crop = crop_img(image)
    gamma = random_gamma(crop)
    # blur_img = blur(gamma)
    shadow_img = shadow(gamma)
    flip_img, steering_angle = random_flip(shadow_img, steering_angle, flipping_prob=0.5)
    small_img = resize(flip_img, new_size=(32, 128))
    return small_img, steering_angle


def select_img(line):
    indicator_img = np.random.randint(0, 3)
    correction = 0.23
    if indicator_img == 0:  # center
        img = cv2.imread(path(line[0]))
        angle = float(line[3])
    elif indicator_img == 1:  # left
        img = cv2.imread(path(line[1]))
        angle = float(line[3]) + correction
    else:  # right
        img = cv2.imread(path(line[2]))
        angle = float(line[3]) - correction
    return img, angle


def visualize(lines):
    # plot three camera view
    plt.figure(figsize=(12,4))
    imtitle1 = ['left', 'center', 'right']
    p = [path(lines[0][1]), path(lines[0][0]), path(lines[0][2])]
    for i in range(3):
        img = mpimg.imread(p[i])
        plt.subplot(1, 3, i+1)
        plt.imshow(img)
        plt.axis('off')
        plt.title(imtitle1[i])
    plt.show()

    # plot image process
    imgs = []
    for i in range(3):
        img = mpimg.imread(p[i])
        crop = crop_img(img)
        imgs.append(crop)
    gamma = random_gamma(imgs[0])
    flip = np.fliplr(imgs[1])
    shadow_img = shadow(imgs[2])
    imgs.append(gamma)
    imgs.append(flip)
    imgs.append(shadow_img)

    plt.figure(figsize=(16, 4))
    imtitle2 = ['Left', 'Center', 'Right', 'Random Gamma', 'Flip', 'Random Shadow']
    for i in range(6):
        plt.subplot(2, 3, i+1)
        plt.imshow(imgs[i])
        plt.axis('off')
        plt.title(imtitle2[i])
    plt.show()

    # plot two Track
    track1 = mpimg.imread('./img/Track1.JPG')
    track2 = mpimg.imread('./img/Track2.JPG')
    plt.figure(figsize=(8,4))
    plt.subplot(121)
    plt.imshow(track1)
    plt.axis('off')
    plt.subplot(122)
    plt.imshow(track2)
    plt.axis('off')


def load_data(lines, batch_size):
    while True:
        x_batch = []
        y_batch = []
        idx = 0
        for line in lines:
            image, angle = select_img(line)
            image_process, angle_process = process_img(image, angle)
            x_batch.append(image_process)
            y_batch.append(angle_process)
            idx += 1
            if idx == batch_size:
                idx = 0
                yield np.array(x_batch), np.array(y_batch)
                x_batch = []
                y_batch = []


def silent_delete(file):
    """
    This method delete the given file from the file system if it is available
    Source: http://stackoverflow.com/questions/10840533/most-pythonic-way-to-delete-a-file-which-may-not-exist
    :param file:
        File to be deleted
    :return:
        None
    """
    try:
        os.remove(file)

    except OSError as error:
        if error.errno != errno.ENOENT:
            raise


def save_model(model, model_name='model_balanced_2.json', weights_name='model_balanced_2.h5'):
    """
    Save the model into the hard disk
    :param model:
        Keras model to be saved
    :param model_name:
        The name of the model file
    :param weights_name:
        The name of the weight file
    :return:
        None
    """
    silent_delete(model_name)
    silent_delete(weights_name)

    json_string = model.to_json()
    with open(model_name, 'w') as outfile:
        json.dump(json_string, outfile)

    model.save_weights(weights_name)


def Model(lines_data):
    model = Sequential()
    model.add(Lambda(lambda x: x / 255.0 - 0.5, input_shape=(32, 128, 3)))
    # model.add(Cropping2D(cropping=((70,25), (0,0))))
    model.add(Convolution2D(24, 5, 5, border_mode='same', subsample=(2, 2)))
    model.add(Activation(activation="relu"))
    model.add(MaxPooling2D(pool_size=(2, 2), strides=(1, 1)))

    model.add(Convolution2D(36, 5, 5, border_mode='same', subsample=(2, 2)))
    model.add(Activation(activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2), strides=(1, 1)))

    model.add(Convolution2D(48, 5, 5, border_mode='same', subsample=(2, 2)))
    model.add(Activation(activation="relu"))
    model.add(MaxPooling2D(pool_size=(2, 2), strides=(1, 1)))

    model.add(Convolution2D(64, 3, 3, border_mode='same', subsample=(1, 1)))
    model.add(Activation(activation="relu"))
    model.add(MaxPooling2D(pool_size=(2, 2), strides=(1, 1)))

    model.add(Convolution2D(64, 3, 3, border_mode='same', subsample=(1, 1)))
    model.add(Activation(activation="relu"))
    model.add(MaxPooling2D(pool_size=(2, 2), strides=(1, 1)))

    model.add(Flatten())

    # Next, five fully connected layers
    model.add(Dense(1164))
    model.add(Activation(activation="relu"))
    model.add(Dropout(0.5))

    model.add(Dense(100))
    model.add(Activation(activation="relu"))

    model.add(Dense(50))
    model.add(Activation(activation="relu"))

    model.add(Dense(10))
    model.add(Activation(activation="relu"))

    model.add(Dense(1))

    model.summary()

    batch_size = 64
    learning_rate = 1e-4

    model.compile(optimizer=Adam(learning_rate), loss="mse", metrics=["accuracy"])

    print('Total data number = {}'.format(len(lines_data)))
    training_num = math.ceil(len(lines_data) * 0.8/batch_size)*batch_size
    print('Training data number = {}'.format(training_num))
    validation_num = math.ceil(len(lines_data) * 0.2/batch_size)*batch_size
    print('Validation data number = {}'.format(validation_num))
    result = model.fit_generator(generator=load_data(lines_data[:training_num], batch_size),
                                 samples_per_epoch=training_num,
                                 nb_epoch=10,
                                 validation_data=load_data(lines_data[-validation_num:], batch_size),
                                 nb_val_samples=validation_num,
                                 verbose=1)

    save_model(model)
    print("Model Saved.")

    # ### plot the training and validation loss for each epoch
    plt.figure()
    plt.plot(result.epoch, result.history['loss'], '-o')
    plt.plot(result.epoch, result.history['val_loss'], '-*')
    plt.title('model mean squared error loss')
    plt.ylabel('mean squared error loss')
    plt.xlabel('epoch')
    plt.legend(['training set', 'validation set'], loc='upper right')
    plt.ylim([0, 0.2])
    plt.show()


def balance(lines, num_bins=500, save_csv=False, plot_histogram=False):

    bin_n = 300  # N of examples to include in each bin (at most)
    balance_box = []
    start = 0
    len_bin = []
    for end in np.linspace(0, 1, num=num_bins)[1:]:

        idx = (angles >= start) & (angles < end)
        n_num = min(bin_n, angles[idx].shape[0])

        sample_idx = sample(range(angles[idx].shape[0]), n_num)
        lines_range = np.array(lines)[idx].tolist()
        len_bin.append(len(sample_idx))
        for i in range(len(sample_idx)):
            balance_box.append(lines_range[sample_idx[i]])
        start = end

    print('Balanced data number = {}'.format(len(balance_box)))

    if plot_histogram:

        plt.figure(figsize=(10, 4))
        rect = plt.bar((np.linspace(0, 1, num=num_bins)[1:]), height=len_bin, width=0.001, alpha=0.6)
        plt.ylim(0, 320)
        plt.xlim(0, 1.)
        plt.title('Steering Angle Distribution')

    if save_csv:
        with open(data_path + 'driving_log_balanced.csv') as csvfile_balance:
            writer = csv.writer(csvfile_balance)
            writer.writerow(balance_box)
            csvfile_balance.close()

    return balance_box

if __name__ == "__main__":

    lines = []
    angles = []
    data_path = './data_backup/'
    with open(data_path + 'driving_log_full.csv') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            lines.append(row)
            angles.append(np.absolute(float(row[3])))
    angles = np.array(angles)
    num_data = len(lines)
    lines = shuffle(lines)
    balanced_data = balance(lines, num_bins=500, save_csv=False, plot_histogram=False)


    print('num_data = {}'.format(len(balanced_data)))
    Model(balanced_data)
