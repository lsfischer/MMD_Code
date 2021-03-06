from tensorflow.python.ops import variable_scope


def get_decoder_embedding(decoder_inputs, num_symbols,
                          embedding_size, output_projection=None,
                          feed_previous=False,
                          update_embedding_for_previous=True, scope=None):
    """RNN decoder with embedding and a pure-decoding option.
    Args:
      decoder_inputs: A list of 1D batch-sized int32 Tensors (decoder inputs).
      initial_state: 2D Tensor [batch_size x cell.state_size].
      cell: rnn_cell.RNNCell defining the cell function.
      num_symbols: Integer, how many symbols come into the embedding.
      embedding_size: Integer, the length of the embedding vector for each symbol.
      output_projection: None or a pair (W, B) of output projection weights and
        biases; W has shape [output_size x num_symbols] and B has
        shape [num_symbols]; if provided and feed_previous=True, each fed
        previous output will first be multiplied by W and added B.
      feed_previous: Boolean; if True, only the first of decoder_inputs will be
        used (the "GO" symbol), and all other decoder inputs will be generated by:
          next = embedding_lookup(embedding, argmax(previous_output)),
        In effect, this implements a greedy decoder. It can also be used
        during training to emulate http://arxiv.org/abs/1506.03099.
        If False, decoder_inputs are used as given (the standard decoder case).
      update_embedding_for_previous: Boolean; if False and feed_previous=True,
        only the embedding for the first symbol of decoder_inputs (the "GO"
        symbol) will be updated by back propagation. Embeddings for the symbols
        generated from the decoder itself remain unchanged. This parameter has
        no effect if feed_previous=False.
      scope: VariableScope for the created subgraph; defaults to
        "embedding_rnn_decoder".
    Returns:
      emb_inp:Embedding for decoder_inputs which is a list of size self.max_len contaning tensor of size batch_size*embedding_size.
      loop_function:Function loop
    Raises:
      ValueError: When output_projection has the wrong shape.
    """
    if output_projection is not None:
        proj_weights = ops.convert_to_tensor(output_projection[0],
                                             dtype=dtypes.float32)
        proj_weights.get_shape().assert_is_compatible_with([None, num_symbols])
        proj_biases = ops.convert_to_tensor(
            output_projection[1], dtype=dtypes.float32)
        proj_biases.get_shape().assert_is_compatible_with([num_symbols])

    with variable_scope.variable_scope(scope or "embedding_rnn_decoder"):
        embedding = variable_scope.get_variable("embedding",
                                                [num_symbols, embedding_size])
        loop_function = _extract_argmax_and_embed(embedding, output_projection,
                                                  update_embedding_for_previous) if feed_previous else None
        emb_inp = (embedding_ops.embedding_lookup(embedding, i) for i in decoder_inputs)
        return emb_inp, loop_function


def _extract_argmax_and_embed(embedding, output_projection=None,
                              update_embedding=True):
    """Get a loop_function that extracts the previous symbol and embeds it.
    Args:
      embedding: embedding tensor for symbols.
      output_projection: None or a pair (W, B). If provided, each fed previous
        output will first be multiplied by W and added B.
      update_embedding: Boolean; if False, the gradients will not propagate
        through the embeddings.
    Returns:
      A loop function.
    """

    def loop_function(prev, _):
        if output_projection is not None:
            prev = nn_ops.xw_plus_b(
                prev, output_projection[0], output_projection[1])
        prev_symbol = math_ops.argmax(prev, 1)
        # Note that gradients will not propagate through the second parameter of
        # embedding_lookup.
        emb_prev = embedding_ops.embedding_lookup(embedding, prev_symbol)
        if not update_embedding:
            emb_prev = array_ops.stop_gradient(emb_prev)
        return emb_prev

    return loop_function


###


import math

from tensorflow.python.framework import dtypes
from tensorflow.python.framework import ops
from tensorflow.python.ops import array_ops
from tensorflow.python.ops import embedding_ops
from tensorflow.python.ops import init_ops
from tensorflow.python.ops import math_ops
from tensorflow.python.ops import nn_ops
from tensorflow.python.ops import rnn_cell_impl
from tensorflow.python.ops import variable_scope as vs
from tensorflow.python.util import nest

RNNCell = rnn_cell_impl.RNNCell
_WEIGHTS_VARIABLE_NAME = rnn_cell_impl._WEIGHTS_VARIABLE_NAME
_BIAS_VARIABLE_NAME = rnn_cell_impl._BIAS_VARIABLE_NAME


# TODO(xpan): Remove this function in a follow up.
def linear(args,
           output_size,
           bias,
           bias_initializer=None,
           kernel_initializer=None):
    """Linear map: sum_i(args[i] * W[i]), where W[i] is a variable.
    Args:
      args: a 2D Tensor or a list of 2D, batch, n, Tensors.
      output_size: int, second dimension of W[i].
      bias: boolean, whether to add a bias term or not.
      bias_initializer: starting value to initialize the bias
        (default is all zeros).
      kernel_initializer: starting value to initialize the weight.
    Returns:
      A 2D Tensor with shape `[batch, output_size]` equal to
      sum_i(args[i] * W[i]), where W[i]s are newly created matrices.
    Raises:
      ValueError: if some of the arguments has unspecified or wrong shape.
    """
    if args is None or (nest.is_sequence(args) and not args):
        raise ValueError("`args` must be specified")
    if not nest.is_sequence(args):
        args = [args]

    # Calculate the total size of arguments on dimension 1.
    total_arg_size = 0
    shapes = [a.get_shape() for a in args]
    for shape in shapes:
        if shape.ndims != 2:
            raise ValueError("linear is expecting 2D arguments: %s" % shapes)
        if shape.dims[1].value is None:
            raise ValueError("linear expects shape[1] to be provided for shape %s, "
                             "but saw %s" % (shape, shape[1]))
        else:
            total_arg_size += shape.dims[1].value

    dtype = [a.dtype for a in args][0]

    # Now the computation.
    scope = vs.get_variable_scope()
    with vs.variable_scope(scope) as outer_scope:
        weights = vs.get_variable(_WEIGHTS_VARIABLE_NAME, [total_arg_size, output_size],
                                  dtype=dtype,
                                  initializer=kernel_initializer)
        if len(args) == 1:
            res = math_ops.matmul(args[0], weights)
        else:
            res = math_ops.matmul(array_ops.concat(args, 1), weights)
        if not bias:
            return res
        with vs.variable_scope(outer_scope) as inner_scope:
            inner_scope.set_partitioner(None)
            if bias_initializer is None:
                bias_initializer = init_ops.constant_initializer(0.0, dtype=dtype)
            biases = vs.get_variable(
                _BIAS_VARIABLE_NAME, [output_size],
                dtype=dtype,
                initializer=bias_initializer)
        return nn_ops.bias_add(res, biases)
