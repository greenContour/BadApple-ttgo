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
        # print("meowwwww")
        vid_cap = cv.VideoCapture(self.vid_path)

        if not vid_cap.isOpened():
            print("Cannot open camera")
            exit(2)

        # print("nya")

        wid = int(vid_cap.get(cv.CAP_PROP_FRAME_WIDTH))
        hei = int(vid_cap.get(cv.CAP_PROP_FRAME_HEIGHT))

        self.dimensions = [wid, hei]
        self.vid_cap = vid_cap
        self.fps = vid_cap.get(cv.CAP_PROP_FPS)

        # print(self.vid_cap, vid_cap)

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

        # self.example_path = example_path
        #
        # if self.example_path is not None:
        #     self.file2r = open(path2write, 'w')

    def close(self):
        # self.file2w.write("const uint{0}_t* const frames[frames_n] PROGMEM".format(self.data_type_size))
        # self.file2w.write(" {")
        #
        # for i in range(1, self.frames_n):
        #     self.file2w.write(self.frame_name + str(i) + ", ")
        #
        #     if (i + 1) % 10 == 0:
        #         self.file2w.write('\n')
        #
        # self.file2w.write("};")

        self.file2w.close()

    def open(self, dims):
        self.vid_dimensions = dims

        self.file2w = open(self.path2write, 'w')

        self.file2w.write("#include <pgmspace.h> \n \n")
        self.file2w.write("const uint16_t frames_n = {0};\n".format(self.frames_n))
        self.file2w.write("\n")

    # def compressFrameType1(self, frame_data):
    #
    #     # p_frame = frames_data[0]
    #     # c_frame = frames_data[1]
    #     #
    #     # frame_cnt = frames_data[2]
    #
    #     # frame_cnt = frame_data[0]
    #
    #     frame = frame_data
    #
    #     compressed_data = [[] for i in range(self.vid_dimensions[1])]
    #
    #     pix_cnt = 1
    #
    #     # p_cnd = False
    #     # c_cnd = False
    #
    #     max_px_cnt = 0
    #
    #     for row_id in range(self.vid_dimensions[1]):
    #         # ppixel = c_frame[row_id][30]
    #         # p_cnd = (p_frame[row_id][30] == c_frame[row_id][30])
    #
    #         ppixel = frame[row_id][30]
    #
    #         for column_id in range(31, 208):
    #             cpixel = frame[row_id][column_id]
    #
    #             if cpixel != ppixel:
    #                 px_val = 0
    #
    #                 if ppixel > 0:
    #                     px_val = 1
    #
    #                 compressed_data[row_id].append([px_val, pix_cnt])
    #                 if pix_cnt > max_px_cnt:
    #                     max_px_cnt = pix_cnt
    #
    #                 pix_cnt = 1
    #             else:
    #                 pix_cnt += 1
    #
    #             ppixel = cpixel
    #             # p_cnd = c_cnd
    #
    #         px_val = 0
    #
    #         if ppixel > 0:
    #             px_val = 1
    #
    #         compressed_data[row_id].append([px_val, pix_cnt])
    #         if pix_cnt > max_px_cnt:
    #             max_px_cnt = pix_cnt
    #
    #         compressed_data[row_id].append(max_px_cnt)
    #
    #         max_px_cnt = 0
    #
    #         self.test_data_struct_1[str(compressed_data[row_id])] = self.test_data_struct_1.get(str(compressed_data[row_id]), 0) + 1
    #         if not self.test_data_struct_2.get(str(compressed_data[row_id]), False):
    #             self.test_data_struct_2[str(compressed_data[row_id])] = compressed_data[row_id]
    #
    #         # print("Check flag:", check_flag, " Checker: ", 178 * self.vid_dimensions[1])
    #         pix_cnt = 1
    #
    #     return [compressed_data]
    #
    # def compressFrameType3(self, frame_data):
    #     frame = frame_data
    #
    #     compressed_data = []
    #
    #     px_cnt = 0
    #
    #     max_px_cnt = 0
    #     min_px_cnt = 23852
    #
    #     ppixel = frame[0][30]
    #
    #     first_px = 0
    #
    #     if ppixel > 0:
    #         first_px = 1
    #
    #     for row_id in range(self.vid_dimensions[1]):
    #         for column_id in range(30, 208):
    #             cpixel = frame[row_id][column_id]
    #
    #             if cpixel != ppixel:
    #
    #                 compressed_data.append(px_cnt)
    #                 if px_cnt > max_px_cnt:
    #                     max_px_cnt = px_cnt
    #
    #                 if px_cnt < min_px_cnt:
    #                     min_px_cnt = px_cnt
    #
    #                 px_cnt = 1
    #             else:
    #                 px_cnt += 1
    #
    #             ppixel = cpixel
    #             # p_cnd = c_cnd
    #
    #     compressed_data.append(px_cnt)
    #     if px_cnt > max_px_cnt:
    #         max_px_cnt = px_cnt
    #
    #     if px_cnt < min_px_cnt:
    #         min_px_cnt = px_cnt
    #
    #     # print(max_px_cnt, min_px_cnt, len(compressed_data))
    #
    #     self.test_data1 += min_px_cnt
    #     self.test_data2 += max_px_cnt
    #
    #     compressed_data.append([first_px, min_px_cnt, max_px_cnt])
    #
    #     # print(compressed_data)
    #
    #     self.test_data_struct_1[str(compressed_data)] = self.test_data_struct_1.get(str(compressed_data), 0) + 1
    #
    #     return compressed_data

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

                # # self.test_data_struct_1[old_ret[-1][1]][old_ret[-1][0]] = (self.test_data_struct_1[old_ret[-1][1]].get(old_ret[-1][0], 0) + 1)
                #
                # self.test_data_struct_1[old_ret[-1][1]][old_ret[-1][0]] = (
                #             self.test_data_struct_1[old_ret[-1][1]].get(old_ret[-1][0], 0) - 1)
                #
                # # self.test_data_struct_1[old_ret[-1][0]] = self.test_data_struct_1.get(old_ret[-1][0], 0) - 1
                #
                # self.average_l_for_colour[old_ret[-1][1]][1] -= old_ret[-1][0]
                # self.average_l_for_colour[old_ret[-1][1]][0] -= 1

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

                    # self.test_data_struct_1[ppixel][px_cnt] = (self.test_data_struct_1[ppixel].get(px_cnt, 0) + 1)
                    # # self.test_data_struct_1[px_cnt] = self.test_data_struct_1.get(px_cnt, 0) + 1
                    # self.test_data_struct_2[ppixel][1] = max(self.test_data_struct_2[ppixel][1], px_cnt)
                    # self.test_data_struct_2[ppixel][0] = min(self.test_data_struct_2[ppixel][0], px_cnt)
                    # self.average_l_for_colour[ppixel][1] += px_cnt
                    # self.average_l_for_colour[ppixel][0] += 1

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

                    # self.test_data_struct_1[ppixel][px_cnt] = (self.test_data_struct_1[ppixel].get(px_cnt, 0) + 1)
                    # self.test_data_struct_2[ppixel][1] = max(self.test_data_struct_2[ppixel][1], px_cnt)
                    # self.test_data_struct_2[ppixel][0] = min(self.test_data_struct_2[ppixel][0], px_cnt)
                    # self.average_l_for_colour[ppixel][1] += px_cnt
                    # self.average_l_for_colour[ppixel][0] += 1

                    px_cnt = 0
                else:
                    px_cnt += 1

                ppixel = cpixel
                # p_cnd = c_cnd

        old_ret.append([px_cnt, ppixel])

        # self.test_data_struct_1[ppixel][px_cnt] = (self.test_data_struct_1[ppixel].get(px_cnt, 0) + 1)
        # self.test_data_struct_2[ppixel][1] = max(self.test_data_struct_2[ppixel][1], px_cnt)
        # self.test_data_struct_2[ppixel][0] = min(self.test_data_struct_2[ppixel][0], px_cnt)
        # self.average_l_for_colour[ppixel][1] += px_cnt
        # self.average_l_for_colour[ppixel][0] += 1

        self.test_data1 += px_cnt + 1

        return old_ret

    def fetchBitString(self, data):
        # # print(data[-5:])
        # first_px = data[-1][0]
        #
        # min_px = data[-1][1]
        # max_px = data[-1][2]
        # bin_min_px = bin(min_px)[2:]
        # bin_max_dif = bin(max_px - min_px)[2:]
        #
        # """
        # bmin = 1
        # bits = 1
        # bitstr = 1
        #
        # """
        #
        # bits_for_min_px = len(bin_min_px) - 1
        # self.test_data3 += bits_for_min_px
        # bit_string = "0" * (4 - len(bin(bits_for_min_px)[2:])) + bin(bits_for_min_px)[2:]
        # bit_string += bin_min_px
        #
        # bits_for_max_dif = len(bin_max_dif)
        # bit_string += "0" * (4 - len(bin(bits_for_max_dif)[2:])) + bin(bits_for_max_dif)[2:]
        #
        # bin_packets_n = bin(len(data) - 1)[2:]
        # bits_for_packet_n = len(bin_packets_n)
        # bit_string += "0" * (4 - len(bin(bits_for_packet_n)[2:])) + bin(bits_for_packet_n)[2:]
        # bit_string += "0" * (bits_for_packet_n - len(bin_packets_n)) + bin_packets_n
        #
        # bit_string += str(first_px)
        #
        # for num in data[:len(data) - 1]:
        #     sub_string_1 = bin(num - min_px)[2:]
        #
        #     bit_string += "0" * (bits_for_max_dif - len(sub_string_1)) + sub_string_1
        #
        # return bit_string

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

        # ret = bin(int(len(data) / self.data_type_size))[2:]
        # ret = "0b" + "0" * (self.data_type_size - len(ret)) + ret + ", "
        # # print(data)
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

        # frame_cnt = data[0]

        # self.file2w.write("const uint{0}_t {1}[] PROGMEM".format(self.data_type_size,
        #                                                                  self.frame_name + str(frame_cnt)))
        #
        # self.file2w.write(" {\n")

        full_bit_string = self.fetchBitString(data)

        # full_bit_string = ""

        # for row_id in range(self.vid_dimensions[1]):
        #     # self.file2w.write("{")
        #
        #     full_bit_string += self.fetchBitString(data)
        #
        #     # self.file2w.write("}, \n")
        #     # self.file2w.write("\n")

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

    # meow1
    # dt_ret = []
    #
    # ret, p_f_data, _ = vid.read()
    #
    # for loop in range(2, frames_n):
    #     ret, c_f_data, _ = vid.read()
    #
    #     if not ret:
    #         break
    #
    #     dt_ret = writer.difFrames(c_f_data, p_f_data, dt_ret)
    #
    #     if loop % 1000 == 0:
    #         print(loop, vid.frame_count)
    #
    #     p_f_data = c_f_data

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
    print("Meow")

    print(frames_n // skip_every)
    print(writer.test_data1)
    print(writer.test_data2)
    print(((vid.dimensions[0] - 60) * vid.dimensions[1]) * ((frames_n - 1) // skip_every))

    print("you are a fool!")

    # fil = open(file="statistics.txt", mode='w')
    #
    # # print(writer.test_data_struct_1[np.uint8(0)])
    #
    # itms_0 = sorted(writer.test_data_struct_1[np.uint8(0)].items(), reverse=True, key=lambda x: x[1])
    # itms_1 = sorted(writer.test_data_struct_1[np.uint8(255)].items(), reverse=True, key=lambda x: x[1])
    #
    # fil.write("Items 255:\n")
    # for k, v in itms_1:
    #     if v == 0:
    #         continue
    #     line = str(k) + " - " + str(v) + ",\n"
    #     fil.write(line)
    #
    # fil.write("Items 0:\n")
    #
    # for k, v in itms_0:
    #     if v == 0:
    #         continue
    #     line = str(k) + " - " + str(v) + ",\n"
    #     fil.write(line)
    #
    # for k, v in writer.test_data_struct_2.items():
    #     print(k, v)
    #
    # fil.write("\nLength sums and block amounts (e.g [10, 30, 9, 33] => 82, 4):\n")
    #
    # line = str(writer.average_l_for_colour)
    # fil.write(line)
    #
    # fil.close()

    # print("MEOW3")
    # print(writer.average_l_for_colour)
    # for k, v in writer.average_l_for_colour.items():
    #     print(k, v[1] / v[0])


    """
    0 673478
    1 325120
    2 193958
    3 127578
    4 91155
    5 71810
    6 54136
    7 43694
    176 43501
    8 36734
    9 32968
    10 28440
    11 25941
    12 23220
    175 23017
    13 21164
    14 19608
    15 18343
    16 17174
    17 16059
    18 14913
    19 14842
    174 13942
    20 13744
    21 13346
    22 12727
    23 12523
    25 12111
    24 11816
    26 11598
    27 11486
    28 11268
    29 11250
    31 11186
    30 10968
    33 10913
    32 10703
    34 10572
    35 10559
    36 10106
    37 10092
    38 9757
    173 9693
    39 9625
    177 9036
    43 8995
    40 8835
    41 8830
    42 8775
    45 8707
    44 8645
    46 8245
    47 8038
    49 7825
    48 7684
    172 7602
    50 7300
    51 7153
    171 6968
    56 6806
    52 6774
    57 6746
    54 6676
    53 6638
    58 6561
    55 6550
    59 6280
    63 6066
    61 6006
    60 5949
    64 5897
    62 5728
    67 5666
    65 5638
    170 5518
    66 5471
    68 5447
    69 5358
    70 5184
    169 5092
    139 5067
    72 5029
    138 4925
    140 4874
    167 4856
    141 4848
    71 4829
    137 4803
    145 4741
    168 4739
    142 4730
    73 4699
    144 4684
    143 4628
    136 4619
    147 4594
    75 4575
    113 4570
    79 4532
    146 4527
    MEOW1
    32767 138
    32284 0
    32182 0
    32172 1
    32045 0
    31806 0
    31567 0
    31328 0
    30890 0
    30722 0
    30591 0
    30517 0
    30378 0
    30352 0
    30278 0
    30188 0
    30113 0
    30039 0
    30011 0
    30006 0
    29949 0
    29874 0
    29392 0
    29153 0
    28914 0
    28675 0
    28436 0
    28196 0
    27591 0
    27486 0
    27460 0
    27386 0
    27221 0
    27147 0
    27057 0
    26982 0
    26774 0
    26500 0
    26261 0
    26159 0
    26109 1
    26022 0
    25783 0
    25544 0
    25359 1
    24804 1
    24699 0
    24568 0
    24494 0
    24355 0
    24329 0
    24255 0
    24165 0
    24090 0
    24029 1
    24016 0
    23988 0
    23983 0
    23956 1
    23926 0
    23922 0
    23912 0
    23851 0
    23696 1
    23685 1
    23660 1
    23596 0
    23401 1
    23369 0
    23320 1
    23297 1
    23140 1
    23130 0
    22984 1
    22963 1
    22959 1
    22942 1
    22916 1
    22896 1
    22891 0
    22871 0
    22783 1
    22652 0
    22639 1
    22623 1
    22605 1
    22596 1
    22588 1
    22524 0
    22432 1
    22428 1
    22419 1
    22413 0
    22396 1
    22337 0
    22295 1
    22245 1
    22221 2
    22192 1
    22107 1
    MEOW2
    0 [0, 32767]
    255 [0, 12700]
    MEOW3
    {np.uint8(0): [1440200, 150344225], np.uint8(255): [1440061, 3441765]}
    0 104.39121302596861
    255 2.390013339712693
    
    """

    writer.close()

    shutil.copy("vid.h", "/Users/admin/Documents/PlatformIO/Projects/ESP32 1.4inch Display/src/vid.h")
