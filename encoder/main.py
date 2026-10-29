import cv2 as cv

import math
import shutil

import numpy as np


class Video:

    def __init__(self, path, start_frame=0, frames_n=-1):
        self.vid_path = path
        self.dimensions = [0, 0]
        self.vid_cap = None
        self.fps = 0
        self.frame_count = 0
        self.start_frame = start_frame
        self.frames_n = frames_n

    def openCap(self):
        vid_cap = cv.VideoCapture(self.vid_path)

        if not vid_cap.isOpened():
            print("Cannot open camera")
            exit(2)

        wid = int(vid_cap.get(cv.CAP_PROP_FRAME_WIDTH))
        hei = int(vid_cap.get(cv.CAP_PROP_FRAME_HEIGHT))

        self.dimensions = [wid, hei]
        self.vid_cap = vid_cap
        self.fps = vid_cap.get(cv.CAP_PROP_FPS)

        if self.start_frame != 0:
            self.skipCap()

        return True

    def skipCap(self):
        ret = True

        while self.frame_count < self.start_frame and ret:
            ret = self.read(True)
            self.frame_count += 1

        self.frame_count = 0

    def _transform(self, frame):

        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

        _, bw = cv.threshold(gray, 128, 255, cv.THRESH_BINARY)

        return bw

    def read(self, skip=False):
        ret, frame = self.vid_cap.read()

        if not ret:
            self.closeCap()

        if ret and not skip:

            ftransf = self._transform(frame)

            self.frame_count += 1

            if self.frame_count == self.frames_n:
                self.closeCap()
                ret = False

            return ret, ftransf, frame

        else:
            return ret, None, None

    def closeCap(self):
        self.vid_cap.release()


class Writer:
    def __init__(self, path2write, frames_n, frame_name="f", data_type_size=64):
        self.path2write = path2write

        self.frames_n = frames_n

        # self.batch_size = batch_bits
        self.data_type_size = data_type_size

        self.file2w = None

        self.vid_dimensions = None

        self.frame_name = frame_name

        self.test_data1 = 0
        self.test_data2 = 0
        self.test_data3 = 0

        self.average_l_for_colour = {np.uint8(0): [0, 0], np.uint8(255): [0, 0]}

        self.test_data_struct_1 = {np.uint8(0): dict(), np.uint8(255): dict()}
        self.test_data_struct_2 = {np.uint8(0): [32768, 0], np.uint8(255): [32768, 0]}

        """
        self.vlq_list = [8, 7] 33.02 mb   
        self.vlq_list = [6, 5, 4] 32.55
        self.vlq_list = [5, 5, 5] ~33+ (34?)
        self.vlq_list = [6, 6, 3] ~33+
        self.vlq_list = [6, 3, 6] 30.2
        self.vlq_list = [4, 4, 7] 30.6
        self.vlq_list = [6, 2, 7] 29.2
        self.vlq_list = [4, 2, 2, 7] 29.2
        self.vlq_list = [5, 2, 8] 31.5
        self.vlq_list = [7, 2, 6] 30.6
        self.vlq_list = [2, 6, 7] 33
        self.vlq_list = [7, 1, 7] 30.2
        self.vlq_list = [6, 2, 2, 5] 29.2
        self.vlq_list = [4, 4, 2, 5] 30.6
        self.vlq_list = [5, 3, 2, 5] 30.6
        """

        # self.vlq_list_0 = [6, 2, 2, 4,]
        # self.vlq_list_1 = [1, 2, 2, 1]

        self.vlq_list_0 = [5, 2, 1, 3, 2, 1, 1, 4, 2]
        self.vlq_list_1 = [5, 2, 1, 3, 2, 1, 1, 4, 2]

        """
        6 2 7 8 29.2
        [5, 2, 1, 3, 2, 2, 6] 28.5
        
        [5, 2, 1, 3, 2, 1, 1, 4, 2]
        
        """

        # self.vlq_list_0 = [6, 2, 5, ]
        # self.vlq_list_1 = [1, 2, 1]

        self.max_vlq_val_0 = pow(2, sum(self.vlq_list_0)) - 1
        self.max_vlq_val_1 = pow(2, sum(self.vlq_list_1)) - 1

        """
        self.vlq_list = [3, 5, 7] 29.8
        
        self.vlq_list_0 = [7, 4, 4,]
        self.vlq_list_1 = [4, 10] 32.6
        
        self.vlq_list_0 = [4, 4, 7,]
        self.vlq_list_1 = [2, 4, 3, 7] 28.2
        
        self.vlq_list_0 = [5, 3, 7,]
        self.vlq_list_1 = [4, 4, 6] 30.1
        
        self.vlq_list_0 = [4, 4, 4, 3]
        self.vlq_list_1 = [2, 2] 27.6
        
        self.vlq_list_0 = [6, 2, 8,]
        self.vlq_list_1 = [1, 2, 2] 26.2
        
        self.vlq_list_0 = [4, 4, 6,]
        self.vlq_list_1 = [2, 2] 27.7
        
        self.vlq_list_0 = [6, 2, 2, 8,]
        self.vlq_list_1 = [1, 2, 2] 26
        
        self.vlq_list_0 = [6, 2, 5,]
        self.vlq_list_1 = [1, 2, 1] 26.1
        
        self.vlq_list_0 = [6, 2, 2, 4,]
        self.vlq_list_1 = [1, 2, 2, 1] 25.7
        
        """
    def close(self):

        self.file2w.close()

    def open(self, dims):
        self.vid_dimensions = dims

        self.file2w = open(self.path2write, 'w')

        self.file2w.write("#include <pgmspace.h> \n \n")
        self.file2w.write("const uint16_t frames_n = {0};\n".format(self.frames_n))
        self.file2w.write("\n")

    def difFrames(self, frame_new, frame_old, old_ret):
        frame_dif = cv.absdiff(frame_new, frame_old)

        ret = self.comppressFrameDyn(frame_dif, old_ret)

        return ret

    def comppressFrameDyn(self, frame, old_ret):

        ppixel = frame[0][30]

        px_cnt = -1

        def check_max_vlq(p_pixel, pix_cnt):
            ret = False

            if p_pixel == np.uint8(0):
                if pix_cnt != self.max_vlq_val_0:
                    ret = True
            else:
                if pix_cnt != self.max_vlq_val_1:
                    ret = True

            return ret

        if old_ret:
            if old_ret[-1][1] == ppixel and check_max_vlq(old_ret[-1][1], old_ret[-1][0]):
                px_cnt = old_ret[-1][0]
                self.test_data1 -= px_cnt + 1
                old_ret.pop(-1)
        else:
            px_colour = 0

            if ppixel > 0:
                px_colour = 1
            old_ret.append(px_colour)

        for row_id in range(self.vid_dimensions[1]):
            for column_id in range(30, 208):
                cpixel = frame[row_id][column_id]

                if not check_max_vlq(cpixel, px_cnt):
                    old_ret.append([px_cnt, ppixel])

                    px_colour = 0
                    if cpixel > 0:
                        px_colour = 1
                    old_ret.append(px_colour)
                    self.test_data1 += px_cnt + 1
                    # self.test_data3 += 1

                    px_cnt = 0

                elif cpixel != ppixel:
                    old_ret.append([px_cnt, ppixel])
                    self.test_data1 += px_cnt + 1
                    px_cnt = 0
                else:
                    px_cnt += 1

                ppixel = cpixel
                # p_cnd = c_cnd

        old_ret.append([px_cnt, ppixel])

        self.test_data1 += px_cnt + 1

        return old_ret

    def fetchBitString(self, data):

        bit_string = ""

        cnt = 0

        # ppair = None

        for dt in data:
            if isinstance(dt, list):
                pxl = dt[0]

                self.test_data2 += pxl + 1

                bits_for_pxl_val = len(bin(pxl)[2:])
                bin_pxl = bin(pxl)[2:]

                pix_colour = dt[1]

                cmlt_bits = 0

                if pix_colour == np.uint8(0):
                    vlq_lis = self.vlq_list_0
                else:
                    vlq_lis = self.vlq_list_1

                for i in range(len(vlq_lis)):
                    sub_str = bin_pxl[-vlq_lis[i]:]

                    cmlt_bits += vlq_lis[i]

                    bin_pxl = bin_pxl[:-vlq_lis[i]]

                    if i == 0:
                        start_bit = "0"
                    else:
                        start_bit = "1"

                    # print(bit_string)

                    bit_string += start_bit + "0" * (vlq_lis[i] - len(sub_str)) + sub_str

                    if cmlt_bits >= bits_for_pxl_val:
                        break
            else:
                bit_string += str(dt)

        return bit_string

    def fetchSegmentedString(self, data):

        ret = ""
        cnt = 0

        for i in range(len(data)):
            if i % self.data_type_size == 0:
                ret += "0b"
                cnt += 1

            # print(i, i % self.data_type_size, i % self.data_type_size == 0, ret)
            ret += data[i]

            if (i + 1) % self.data_type_size == 0:
                ret += ", "

            if ((i + 1) / self.data_type_size) % 3 == 0:
                ret += "\n"

        bin_cnt_l = len(bin(cnt)[2:])

        for i in range(0, 3):
            l = 8 * 2 ** i

            if l >= bin_cnt_l:
                self.file2w.write("\nconst uint{0}_t byte_n = {1};\n".format(l, cnt))
                break

        return ret

    def writeData(self, data):

        full_bit_string = self.fetchBitString(data)

        segm_string = self.fetchSegmentedString(full_bit_string)

        self.file2w.write("const uint{0}_t v[] PROGMEM".format(self.data_type_size))

        self.file2w.write(" {\n")

        self.file2w.write(segm_string)

        self.file2w.write("};\n\n")


"""
134

238
178
"""


if __name__ == "__main__":
    start_frame = 0
    # frames_n = 6570
    frames_n = 6570

    skip_every = 3

    vid = Video("Touhou - Bad AppleCR.mp4", start_frame, frames_n)

    vid.openCap()

    print(vid.dimensions)

    writer = Writer("vid.h", frames_n // skip_every, "f")

    writer.open(vid.dimensions)

    dt_ret = []

    for loop in range(1, frames_n // skip_every):
        ret, c_f_data, _ = vid.read()
        vid.read(True)
        vid.read(True)

        if not ret:
            break

        dt_ret = writer.comppressFrameDyn(c_f_data, dt_ret)

        if loop % 1000 == 0:
            print(loop, vid.frame_count)

    writer.writeData(dt_ret)

    print(frames_n // skip_every)
    print(writer.test_data1)
    print(writer.test_data2)
    print(((vid.dimensions[0] - 60) * vid.dimensions[1]) * ((frames_n - 1) // skip_every))

    writer.close()
