import os
import numpy as np
import pickle as pkl
from params_v2 import *
from annoy import AnnoyIndex
from prepare_data_for_hred import PrepareData

start_symbol_index = 0
end_symbol_index = 1
unk_symbol_index = 2
pad_symbol_index = 3

annoyIndex = None


def load_image_representation(image_annoy_dir):
    annoyIndex = AnnoyIndex(4096, metric='euclidean')

    image_annoy_dir = "/home/l.fischer/MMD_Code/image_annoy_index/annoy.ann"
    annoyIndex.load(image_annoy_dir)
    # annoyPkl = pkl.load(open(image_annoy_dir + '/ImageUrlToIndex.pkl'))


def get_dialog_dict(param, is_test=False):
    train_dir_loc = param['train_dir_loc']
    valid_dir_loc = param['valid_dir_loc']
    test_dir_loc = param['test_dir_loc']
    dump_dir_loc = param['dump_dir_loc']
    vocab_file = param['vocab_file']
    vocab_stats_file = param['vocab_stats_file']
    vocab_freq_cutoff = param['vocab_freq_cutoff']
    train_data_file = param['train_data_file']
    valid_data_file = param['valid_data_file']
    test_data_file = param['test_data_file']
    max_utter = param['max_utter']
    max_len = param['max_len']
    max_images = param['max_images']
    if 'test_state' in param:
        test_state = param['test_state']
    else:
        test_state = None
    preparedata = PrepareData(max_utter, max_len, max_images, start_symbol_index, end_symbol_index, unk_symbol_index,
                              pad_symbol_index, "text", cutoff=vocab_freq_cutoff)
    if os.path.isfile(vocab_file):
        print('found existing vocab file in ' + str(vocab_file) + ', ... reading from there')
    if not is_test:
        print(train_dir_loc)
        print(vocab_file)
        preparedata.prepare_data(train_dir_loc, vocab_file, vocab_stats_file, os.path.join(dump_dir_loc, "train"),
                                 train_data_file, isTrain=True)
        preparedata.prepare_data(valid_dir_loc, vocab_file, vocab_stats_file, os.path.join(dump_dir_loc, "valid"),
                                 valid_data_file, isTrain=True)
    if test_state is not None:
        preparedata.prepare_data(test_dir_loc, vocab_file, vocab_stats_file,
                                 os.path.join(dump_dir_loc + "/test_data_file_state/", "test_" + test_state),
                                 test_data_file, False, True, test_state)
    else:
        preparedata.prepare_data(test_dir_loc, vocab_file, vocab_stats_file, os.path.join(dump_dir_loc, "test"),
                                 test_data_file, False, True, test_state)


def get_weights(padded_target, batch_size, max_len, actual_seq_len):
    remaining_seq_len = max_len - actual_seq_len
    weights = [[1.] * actual_seq_len_i + [0.] * remaining_seq_len_i for actual_seq_len_i, remaining_seq_len_i in
               zip(actual_seq_len, remaining_seq_len)]
    weights = np.asarray(weights)
    # print 'weights shape ', weights.shape
    return weights


def get_utter_seq_len(dialogue_text_dict, dialogue_image_dict, dialogue_target, max_len, max_images, image_rep_size,
                      max_utter, batch_size):
    padded_utters_id = np.asarray([[xij for xij in dialogue_i] for dialogue_i in dialogue_text_dict])
    padded_image_rep = np.asarray([[xij for xij in dialogue_i] for dialogue_i in dialogue_image_dict])
    padded_target = np.asarray([xi for xi in dialogue_target])

    pad_to_target = np.reshape(np.asarray([pad_symbol_index] * batch_size), (batch_size, 1))
    padded_decoder_input = np.concatenate((pad_to_target, padded_target[:, :-1]), axis=1)
    decoder_seq_len = [-1] * batch_size
    row, col = np.where(padded_target == end_symbol_index)
    for row_i, col_i in zip(row, col):
        decoder_seq_len[row_i] = col_i
    if -1 in decoder_seq_len:
        raise Exception('cannot find end symbol in training dialogue')
    decoder_seq_len = np.asarray(decoder_seq_len)
    decoder_seq_len = decoder_seq_len + 1
    return padded_utters_id, padded_image_rep, padded_target, padded_decoder_input, decoder_seq_len


def get_batch_data(max_len, max_images, image_rep_size, max_utter, batch_size, data_dict):
    # get batch_text_dict, batch_image_dict, batch_target_dict from data_dict
    # data_dict is a batch_size sized list of zips(batch_text_dict, batch_image_dict, batch_target)

    data_dict = np.asarray(data_dict)
    # converting data dict from a multidimensional list to a numpy matrix in order to carry out the operations below

    batch_text_dict = data_dict[:, 0]
    # batch_text_dict is a multidimensional list integers (word ids) of dimension batch_size * max_utter * max_len

    batch_image_dict = data_dict[:, 1]
    # batch_image_dict is a multidimensional list of strings of dimension batch_size * max_utter * max_images

    batch_target = data_dict[:, 2]
    # batch_target is a list of list of words ids of dimension batch_size * max_len

    if len(data_dict) % batch_size != 0:
        batch_text_dict, batch_image_dict, batch_target = check_padding(batch_text_dict, batch_image_dict, batch_target,
                                                                        max_len, max_images, max_utter, batch_size)

    batch_image_dict = [
        [[get_image_representation(entry_ijk, image_rep_size) for entry_ijk in data_dict_ij] for data_dict_ij in
         data_dict_i] for data_dict_i in batch_image_dict]

    # batch_image_dict is now transformed to a multidimensional list of image_representations of dimension batch_size * max_utter * max_images * image_rep_size

    padded_utters, padded_image_rep, padded_target, padded_decoder_input, decoder_seq_len = get_utter_seq_len(
        batch_text_dict, batch_image_dict, batch_target, max_len, max_images, image_rep_size, max_utter, batch_size)

    # padded_utters is of dim (batch_size, max_utter,  max_len)
    # padded_image_rep is of dim (batch_size, max_utter, max_images, image_rep_size)
    # padded_target is of dim (batch_size, max_len)
    # padded_decoder_input is of dim (batch_size, max_len)

    padded_weights = get_weights(padded_target, batch_size, max_len, decoder_seq_len)
    # padded_weights is of dim (batch_size, max_len)

    padded_utters, padded_image_rep, padded_target, padded_decoder_input, padded_weights = transpose_utterances(
        padded_utters, padded_image_rep, padded_target, padded_decoder_input, padded_weights)

    # after transposing, padded_utters is of dim (max_utter, max_len, batch_size)
    # after transposing, padded_image_rep is of dim (max_utter, max_images, batch_size, image_rep_size)
    # after transposing, padded_target is of dim (max_len, batch_size)
    # after transposing, padded_decoder_input is of dim (max_len, batch_size)
    # after transposing padded_weights is of dim (max_len, batch_size)
    x
    return padded_utters, padded_image_rep, padded_target, padded_decoder_input, padded_weights


def get_image_representation(image_filename, image_rep_size):
    image_filename = image_filename.strip()
    if image_filename == "":
        return [0.] * image_rep_size
    try:
        return annoyIndex.get_item_vector(annoyPkl[image_filename])
    except:
        return [0.] * image_rep_size


def transpose_utterances(padded_utters, padded_image_rep, padded_target, padded_decoder_input, padded_weights):
    padded_transposed_utters = padded_utters.transpose((1, 2, 0))
    padded_transposed_image_rep = padded_image_rep.transpose((1, 2, 0, 3))
    padded_transposed_target = padded_target.transpose((1, 0))
    padded_transposed_decoder_input = padded_decoder_input.transpose((1, 0))
    padded_transposed_weights = padded_weights.transpose((1, 0))
    return padded_transposed_utters, padded_transposed_image_rep, padded_transposed_target, padded_transposed_decoder_input, padded_transposed_weights


def batch_padding_text(data_mat, max_len, max_utter, pad_size):
    empty_data = [start_symbol_index, end_symbol_index] + [pad_symbol_index] * (max_len - 2)
    empty_data = [empty_data] * max_utter
    empty_data_mat = [empty_data] * pad_size
    data_mat = data_mat.tolist()
    data_mat.extend(empty_data_mat)
    return data_mat


def batch_padding_image(data_mat, max_images, max_utter, pad_size):
    empty_data = [''] * max_images
    empty_data = [empty_data] * max_utter
    empty_data_mat = [empty_data] * pad_size
    data_mat = data_mat.tolist()
    data_mat.extend(empty_data_mat)
    return data_mat


def batch_padding_target_text(data_mat, max_len, pad_size):
    empty_data = [start_symbol_index, end_symbol_index] + [pad_symbol_index] * (max_len - 2)
    empty_data = [empty_data] * pad_size
    data_mat = data_mat.tolist()
    data_mat.extend(empty_data)
    return data_mat


def check_padding(batch_text_dict, batch_image_dict, batch_target, max_len, max_images, max_utter, batch_size):
    pad_size = batch_size - len(batch_target) % batch_size
    batch_text_dict = batch_padding_text(batch_text_dict, max_len, max_utter, pad_size)
    batch_image_dict = batch_padding_image(batch_image_dict, max_images, max_utter, pad_size)
    batch_target = batch_padding_target_text(batch_target, max_len, pad_size)
    return batch_text_dict, batch_image_dict, batch_target


def load_valid_test_target(data_dict):
    return np.asarray(data_dict)[:, 2]


if __name__ == "__main__":
    data_dir = '/nas/Datasets/mmd/v2'
    dump_dir = '/home/l.fischer/MMD_Code/Target_model'

    param = get_params(data_dir=data_dir, dir=dump_dir)
    train_dir_loc = param['train_dir_loc']
    valid_dir_loc = param['valid_dir_loc']
    test_dir_loc = param['test_dir_loc'].replace('test', 'test_smallest')
    dump_dir_loc = param['dump_dir_loc']
    vocab_file = param['vocab_file']
    vocab_stats_file = param['vocab_stats_file']
    vocab_freq_cutoff = param['vocab_freq_cutoff']
    train_data_file = param['train_data_file']
    valid_data_file = param['valid_data_file']
    test_data_file = param['test_data_file'].replace('test', 'test_smallest')
    max_utter = param['max_utter']
    max_len = param['max_len']
    max_images = param['max_images']
    preparedata = PrepareData(max_utter, max_len, max_images, start_symbol_index, end_symbol_index, unk_symbol_index,
                              pad_symbol_index, "text", cutoff=vocab_freq_cutoff)
    if os.path.isfile(vocab_file):
        print('found existing vocab file in ' + str(vocab_file) + ', ... reading from there')
    preparedata.prepare_data(test_dir_loc, vocab_file, vocab_stats_file, os.path.join(dump_dir_loc, "test_smallest"),
                             test_data_file, isTrain=True)
