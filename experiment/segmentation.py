import os
import numpy as np
import sys
from utils.stl_slicer import get_cross_section
from utils.open_save_file import get_file_name, save_file, get_label
from preprocess.stl_to_image import point_sampling

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt


augment_config = [0, 1, 2, 3, -1, -2, -3, 180, 179, 178, 177, 181, 182, 183]
# augment_config = [0]
degree = [0, 45, 90, 135]


def find_slope(point1, point2):  # function to find top line
    if point1[0] == point2[0]:
        return 0
    else:
        return (point1[1] - point2[1]) / (point1[0] - point2[0])


def get_segment(points, mode=None, margin=0, file_name=None):
    """
    Split tooth cross-section into 3 parts, left, right and top. Return one part back
    :param points: ndarray of N*2
    :param mode: String, [left, right, top, debug] -> select which part to return
    :param margin: Float, amount of margin from minimum line
    :param file_name: Name of image
    :return: ndarray of segmented image or saved image
    """
    # Turn into numpy
    points = np.asarray(points)

    # Find max and min x to find sharp point of tooth
    x_min_index = np.argmin(points, axis=0)[0]
    x_max_index = np.argmax(points, axis=0)[0]

    left_point = points[x_min_index, :]
    right_point = points[x_max_index, :]

    # Initial slope, (Move by +20 points to avoid corner of the curve which could provide a unusually large slope)
    top_left_index = x_min_index + 20
    top_right_index = x_max_index - 20
    left_slope = find_slope(left_point, points[top_left_index])
    right_slope = find_slope(right_point, points[top_right_index])
    slope_track = []
    # Find largest slope point, choose as top_left and top_right
    for i in range(top_left_index, top_right_index):
        # For left side, find the steepest slope
        new_left_slope = find_slope(points[x_min_index, :], points[i, :])
        if new_left_slope > left_slope and new_left_slope > 0:
            left_slope = new_left_slope
            top_left_index = i
        # For right side, find the steepest negative slope
        new_right_slope = find_slope(points[x_max_index, :], points[i, :])
        slope_track.append([new_right_slope, points[i, :]])
        if new_right_slope < right_slope and new_right_slope < 0:
            right_slope = new_right_slope
            top_right_index = i

    # Current coordinates: x_min_index, top_left_index, x_max_index, top_right_index
    if mode == "left":
        # If there is margin, choose points slightly below x_min_index
        if margin > 0:
            segmented_points = points[0:top_left_index + 1, :]
            segmented_points = segmented_points[segmented_points[:, 1] > points[x_min_index, 1] - margin]
        else:
            segmented_points = points[x_min_index:top_left_index + 1, :]
        x = segmented_points[:, 0]
        y = segmented_points[:, 1]
    elif mode == "right":
        if margin > 0:
            segmented_points = points[top_right_index:, :]
            segmented_points = segmented_points[segmented_points[:, 1] > points[x_max_index, 1] - margin]
        else:
            segmented_points = points[top_right_index:x_max_index + 1, :]
        x = segmented_points[:, 0]
        y = segmented_points[:, 1]
    elif mode == "top":
        segmented_points = points[top_left_index:top_right_index + 1, :]
        x = segmented_points[:, 0]
        y = segmented_points[:, 1]
    else:
        # Display entire tooth
        mode = None
        segmented_points = points
        x = points[:, 0]
        y = points[:, 1]

    # print(np.shape(x))

    # Plotting
    dpi = 100
    img_size = 800
    fig = plt.figure(figsize=(img_size / dpi, img_size / dpi), dpi=dpi)
    ax = fig.gca()
    min_x, max_x, min_y, max_y = -6, 6, -6, 6
    if mode is None:
        ax.axis([min_x, max_x, min_y, max_y])
        ax.set_autoscale_on(False)  # allows us to define scale
    ax.plot(x, y, linewidth=1.0)

    if file_name is not None:
        # plot lines for viewing
        x1 = range(-6, 6)
        yleft = np.full((10,), points[top_left_index, :][1])
        yright = np.full((10,), points[top_right_index, :][1])
        ax.plot(x1, yleft, '-c')
        ax.plot(x1, yright, '-r')
        if (mode is None) or (mode == "left"):
            ybottom_left = np.full((10,), points[x_min_index, :][1] - margin)
            ax.plot(x1, ybottom_left, '-py')
            ybottom_left = np.full((10,), points[x_min_index, :][1])
            ax.plot(x1, ybottom_left, '-y')
        if (mode is None) or (mode == "right"):
            ybottom_right = np.full((10,), points[x_max_index, :][1] - margin)
            ax.plot(x1, ybottom_right, '-pb')
            ybottom_right = np.full((10,), points[x_max_index, :][1])
            ax.plot(x1, ybottom_right, '-b')
        fig.savefig(file_name, bbox_inches='tight')
        plt.close('all')
    return segmented_points


def get_segment_multiple(name, margin=0, point_only=False, fix_point=None, no_line=False,
                         save_base_dir="../data/segment_2",
                         csv_dir='../../global_data/Ground Truth Score_new.csv'):
    """
    Get a segments of cross section from multiple files, used to train
    :param name: Stl directory
    :param margin: Float, amount of margin from minimum line
    :param point_only: Boolean, save only point file
    :param fix_point: integer, number of point for .npy file. None if doesn't want sampling
    :param no_line: Boolean, True if want to show cutoff line between sections
    :param save_base_dir: String, directory to save file and everything
    :param csv_dir: Directory of score file (.csv format)
    :return: ndarray of segmented image or saved image (Not sure)
    """
    save_dir = [save_base_dir + "/full/", save_base_dir + "/left/", save_base_dir + "/left_point/",
                save_base_dir + "/right/",
                save_base_dir + "/right_point/", save_base_dir + "/top/", save_base_dir + "/top_point/"]
    for s in save_dir:  # Create directory if not exist
        if not os.path.exists(s):
            os.makedirs(s)
    name_dir, image_name = get_file_name(folder_name=name, file_name="PreparationScan.stl")

    error_file_names_all = []  # Used to record error file

    # For saving score.csv
    data_type = ["Occ_B", "Occ_F", "Occ_L", "Occ_Sum", "BL", "MD", "Taper_Sum", "Integrity", "Width", "Surface",
                 "Sharpness"]
    stat_type = ["median"]
    label = dict()
    label_header = ["name"]
    for d in data_type:
        for s in stat_type:
            l, label_name = get_label(d, s, double_data=False, one_hotted=False, normalized=False, file_dir=csv_dir)
            label[d + "_" + s] = l
            label_header.append(d + "_" + s)

    # Number of data should be the same as number of label
    if image_name != label_name:
        print(image_name)
        print(label_name)
        diff = list(set(image_name).symmetric_difference(set(label_name)))
        raise Exception("ERROR, image and label not similar: %d images, %d labels. Possible missing files: %s"
                        % (len(image_name), (len(label_name)), diff))

    label_all = {k: [] for k in dict.fromkeys(label.keys())}
    label_name_all = []

    for image_index, (n_name, im_name) in enumerate(zip(name_dir, image_name)):
        if image_index % 50 == 0:
            print("Progress: %s out of %s, current image: %s" % (image_index, len(image_name), im_name))
        label_name_temp = []
        image_index += 1
        points_all = get_cross_section(n_name, 0, degree, augment=augment_config, axis=1)

        for index, point in enumerate(points_all):  # Enumerate over all augmentation points
            augment_val = augment_config[index]
            if augment_val < 0:
                augment_val = "n" + str(abs(augment_val))
            else:
                augment_val = str(abs(augment_val))
            if point is None:
                error_file_names_all.append("PreparationScan_%s_%s" % (im_name, augment_val))
            else:
                label_name_temp.append(im_name + "_" + augment_val)
                for d in range(len(degree)):
                    file_name = "PreparationScan_%s_%s_%d.png" % (im_name, augment_val, degree[d])
                    file_name_point = "PreparationScan_%s_%s_%d.npy" % (im_name, augment_val, degree[d])
                    # Turn into numpy
                    points = np.asarray(point[d])

                    # Find max and min x to find sharp point of tooth
                    x_min_index = np.argmin(points, axis=0)[0]
                    x_max_index = np.argmax(points, axis=0)[0]

                    left_point = points[x_min_index, :]
                    right_point = points[x_max_index, :]

                    # Initial slope, (+20 points to avoid corner of the curve which could provide a unusually large slope)
                    top_left_index = x_min_index + 20
                    top_right_index = x_max_index - 20
                    left_slope = find_slope(left_point, points[top_left_index])
                    right_slope = find_slope(right_point, points[top_right_index])
                    slope_track = []
                    # Find largest slope point, choose as top_left and top_right
                    for i in range(top_left_index, top_right_index):
                        # For left side, find the steepest slope
                        new_left_slope = find_slope(points[x_min_index, :], points[i, :])
                        if new_left_slope > left_slope and new_left_slope > 0:
                            left_slope = new_left_slope
                            top_left_index = i
                        # For right side, find the steepest negative slope
                        new_right_slope = find_slope(points[x_max_index, :], points[i, :])
                        slope_track.append([new_right_slope, points[i, :]])
                        if new_right_slope < right_slope and new_right_slope < 0:
                            right_slope = new_right_slope
                            top_right_index = i

                    # Current coordinates: x_min_index, top_left_index, x_max_index, top_right_index
                    # Plotting
                    if point_only:
                        # Left
                        # If there is margin, choose points slightly below x_min_index
                        segmented_points = points[0:top_left_index, :]
                        # if margin > 0:
                        #     segmented_points = points[0:top_left_index + 1, :]
                        #     segmented_points = segmented_points[
                        #         segmented_points[:, 1] > points[x_min_index, 1] - margin]
                        # else:
                        #     segmented_points = points[x_min_index:top_left_index + 1, :]
                        if fix_point is not None:
                            segmented_points = point_sampling(segmented_points, fix_point)

                        np.save(save_base_dir + "/left_point/" + file_name_point, segmented_points)

                        # Right
                        segmented_points = points[top_right_index:, :]
                        # if margin > 0:
                        #     segmented_points = points[top_right_index:, :]
                        #     segmented_points = segmented_points[
                        #         segmented_points[:, 1] > points[x_max_index, 1] - margin]
                        # else:
                        #     segmented_points = points[top_right_index:x_max_index + 1, :]

                        if fix_point is not None:
                            segmented_points = point_sampling(segmented_points, fix_point)
                        np.save(save_base_dir + "/right_point/" + file_name_point, segmented_points)

                        # Top
                        segmented_points = points[top_left_index:top_right_index, :]
                        if fix_point is not None:
                            segmented_points = point_sampling(segmented_points, fix_point)
                        np.save(save_base_dir + "/top_point/" + file_name_point, segmented_points)
                    else:
                        dpi = 100
                        img_size = 800
                        fig = plt.figure(figsize=(img_size / dpi, img_size / dpi), dpi=dpi)
                        ax = fig.gca()
                        min_x, max_x, min_y, max_y = -6, 6, -6, 6
                        ax.axis([min_x, max_x, min_y, max_y])
                        ax.set_autoscale_on(False)  # allows us to define scale
                        # plot lines for viewing
                        x1 = range(-6, 6)
                        yleft = np.full((12,), points[top_left_index, :][1])
                        yright = np.full((12,), points[top_right_index, :][1])
                        ybottom_left_margin = np.full((12,), points[x_min_index, :][1] - margin)
                        ybottom_right_margin = np.full((12,), points[x_max_index, :][1] - margin)
                        ybottom_left = np.full((12,), points[x_min_index, :][1])
                        ybottom_right = np.full((12,), points[x_max_index, :][1])

                        # Display entire tooth
                        segmented_points = points
                        x = points[:, 0]
                        y = points[:, 1]

                        ax.plot(x, y, linewidth=1.0)
                        if not no_line:
                            ax.plot(x1, yleft, '-c')
                            ax.plot(x1, yright, '-r')
                            ax.plot(x1, ybottom_left_margin, '-py')
                            ax.plot(x1, ybottom_left, '-y')
                            ax.plot(x1, ybottom_right_margin, '-pb')
                            ax.plot(x1, ybottom_right, '-b')

                        fig.savefig(save_base_dir + "/full/" + file_name, bbox_inches='tight')
                        plt.clf()
                        # plt.close()

                        ax = fig.gca()
                        ax.relim()
                        ax.autoscale()

                        # Left
                        segmented_points = points[0:top_left_index, :]
                        # If there is margin, choose points slightly below x_min_index
                        # if margin > 0:
                        #     segmented_points = points[0:top_left_index + 1, :]
                        #     segmented_points = segmented_points[
                        #         segmented_points[:, 1] > points[x_min_index, 1] - margin]
                        # else:
                        #     segmented_points = points[x_min_index:top_left_index + 1, :]
                        x = segmented_points[:, 0]
                        y = segmented_points[:, 1]

                        ax.axis([min_x, max_x, min_y, max_y])
                        ax.set_autoscale_on(False)  # allows us to define scale

                        ax.plot(x, y, linewidth=1.0)
                        ax.plot(x1, yleft, '-c')
                        ax.plot(x1, ybottom_left_margin, '-py')
                        ax.plot(x1, ybottom_left, '-y')
                        if fix_point is not None:
                            segmented_points = point_sampling(segmented_points, fix_point)
                        fig.savefig(save_base_dir + "/left/" + file_name, bbox_inches='tight')
                        np.save(save_base_dir + "/left_point/" + file_name_point, segmented_points)

                        plt.clf()
                        # plt.close()
                        ax = fig.gca()
                        # Right
                        segmented_points = points[top_right_index:, :]
                        # if margin > 0:
                        #     segmented_points = points[top_right_index:, :]
                        #     segmented_points = segmented_points[
                        #         segmented_points[:, 1] > points[x_max_index, 1] - margin]
                        # else:
                        #     segmented_points = points[top_right_index:x_max_index + 1, :]
                        x = segmented_points[:, 0]
                        y = segmented_points[:, 1]
                        ax.axis([min_x, max_x, min_y, max_y])
                        ax.set_autoscale_on(False)  # allows us to define scale
                        ax.plot(x, y, linewidth=1.0)
                        # ax.plot(x1, yleft, '-c')
                        ax.plot(x1, yright, '-r')
                        ax.plot(x1, ybottom_right_margin, '-pb')
                        ax.plot(x1, ybottom_right, '-b')
                        if fix_point is not None:
                            segmented_points = point_sampling(segmented_points, fix_point)
                        fig.savefig(save_base_dir + "/right/" + file_name, bbox_inches='tight')
                        np.save(save_base_dir + "/right_point/" + file_name_point, segmented_points)
                        plt.clf()

                        # Top
                        ax = fig.gca()
                        segmented_points = points[top_left_index:top_right_index, :]
                        x = segmented_points[:, 0]
                        y = segmented_points[:, 1]
                        ax.axis([min_x, max_x, min_y, max_y])
                        ax.set_autoscale_on(False)  # allows us to define scale
                        ax.plot(x, y, linewidth=1.0)
                        ax.set_xlim([min_x, max_x])
                        ax.plot(x1, yleft, '-c')
                        ax.plot(x1, yright, '-r')
                        if fix_point is not None:
                            segmented_points = point_sampling(segmented_points, fix_point)
                        fig.savefig(save_base_dir + "/top/" + file_name, bbox_inches='tight')
                        np.save(save_base_dir + "/top_point/" + file_name_point, segmented_points)
                        plt.clf()
                        plt.close()

        # Add all label (augmented included)
        for key, value in label.items():
            label_all[key] += [value[image_index] for _ in range(len(label_name_temp))]
        label_name_all += label_name_temp  # Also add label name to the big one

    label_all["name"] = label_name_all
    for s in save_dir:
        open(s + "error_file.txt", 'w').close()
        open(s + "config.txt", 'w').close()
        with open(s + "error_file.txt", 'w') as filehandle:
            for listitem in error_file_names_all:
                filehandle.write('%s\n' % listitem)
        with open(s + "config.txt", 'w') as filehandle:
            filehandle.write('%s\n' % len(degree))
            filehandle.write('%s\n' % len(augment_config))
        save_file(s + "score.csv", label_all, data_format="dict_list", field_name=label_header)
    print("Finish saving file at %s" % save_base_dir)


if __name__ == '__main__':
    # NOTE: Run on jupyter notebook
    get_segment_multiple(margin=0,
                         name='../../global_data/stl_data',
                         save_base_dir="../data/segment_14",
                         # csv_dir="../../global_data/Ground Truth Score_debug.csv",
                         point_only=False, fix_point=50, no_line=True)
