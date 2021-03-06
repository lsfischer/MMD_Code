from tensorflow.contrib.rnn import GRUCell


def get_params(data_dir, dir, image_annoy_dir):
    """
    Creates a dictionary containing all the system parameters to be used in the v2 dataset
    :param data_dir: The path to the data folder (/nas/Datasets/mmd/v2)
    :param dir: The path to output folder (/home/l.fischer/MMD_Code/Target_model)
    :param image_annoy_dir: The path to image_annoy (/home/l.fischer/MMD_Code/image_annoy_index) not being used
    :return: The dictionary object containing all the system parameters
    """

    param = {}
    dir = str(dir)
    param['train_dir_loc'] = data_dir + "/train/"
    param['valid_dir_loc'] = data_dir + "/valid/"
    param['test_dir_loc'] = data_dir + "/test/"
    param['dump_dir_loc'] = dir + "/dump/"
    param['test_output_dir'] = dir + "/test_output/"
    param['vocab_file'] = dir + "/vocab.pkl"
    param['image_annoy_dir'] = image_annoy_dir
    param['train_data_file'] = dir + "/dump/train_data_file.pkl"
    param['valid_data_file'] = dir + "/dump/valid_data_file.pkl"
    param['test_data_file'] = dir + "/dump/test_data_file.pkl"
    param['vocab_file'] = dir + "/vocab.pkl"
    param['vocab_stats_file'] = dir + "/vocab_stats.pkl"
    param['model_path'] = dir + "/model"
    param['terminal_op'] = dir + "/terminal_output.txt"
    param['logs_path'] = dir + "/log"
    param['text_embedding_size'] = 512
    param['image_rep_size'] = 4096
    param['image_embedding_size'] = 512
    param['activation'] = None  # tf.tanh
    param['output_activation'] = None  # tf.nn.softmax
    param['cell_size'] = 512
    param['cell_type'] = GRUCell
    param['batch_size'] = 64
    param['vocab_freq_cutoff'] = 2
    param['learning_rate'] = 0.0004
    param['patience'] = 200
    param['early_stop'] = 100
    param['max_epochs'] = 1000000
    param['max_len'] = 20
    param['max_images'] = 1
    param['num_images_per_utterance'] = 5
    param['max_utter'] = 2 * param['num_images_per_utterance']
    param['print_train_freq'] = 1000
    param['show_grad_freq'] = 2000
    param['valid_freq'] = 10000
    param['max_gradient_norm'] = 0.1
    param['train_loss_incremenet_tolerance'] = 0.01

    # New Parameters
    param['tb_store_loss_freq'] = 1000
    return param
