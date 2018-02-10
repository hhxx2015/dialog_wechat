# -*- coding: utf-8 -*-

import os

import tensorflow as tf

from src import data_load
from src.model import ChatModel


model_dir = r'./model'

num_word = 26102
embedding_dim = 128
max_epoch = 1000

encoder_rnn_state_size = 100
decoder_rnn_state_size = 100
attention_num_units = 100
attention_depth = 100
beam_width = 5
learning_rate = 0.01
decay_steps = 1e4
decay_factor = 0.3
minimum_learning_rate = 1e-5


batch_data = data_load.DataLoader()
batch_size = 30


def run_train():
    max_iteration = batch_data.max_sentence_length + 1
    chat_model = ChatModel(max_iteration, batch_size)
    decoder_results = chat_model.encoder_decoder_graph()
    seq_loss = chat_model.loss(decoder_results)
    with tf.variable_scope('train'):
        train_step = tf.Variable(0, name='global_step', trainable=False)
        lr = tf.train.exponential_decay(
            learning_rate,
            train_step,
            decay_steps,
            decay_factor,
            staircase=True
        )
        lr = tf.clip_by_value(lr, minimum_learning_rate, learning_rate, name='lr_clip')
        opt = tf.train.AdamOptimizer(learning_rate=lr)
        train_variables = tf.trainable_variables()
        grads_vars = opt.compute_gradients(seq_loss, train_variables)
        for i, (grad, var) in enumerate(grads_vars):
            grads_vars[i] = (tf.clip_by_norm(grad, 1.0), var)

        apply_gradient_op = opt.apply_gradients(grads_vars, global_step=train_step)
        with tf.control_dependencies([apply_gradient_op]):
            train_op = tf.no_op(name='train_step')

    saver = tf.train.Saver(tf.global_variables())
    with tf.Session() as sess:
        sess.run([tf.global_variables_initializer(), tf.local_variables_initializer()])
        checkpoint = tf.train.latest_checkpoint(model_dir)
        if checkpoint:
            saver.restore(sess, checkpoint)
        for epoch in range(max_epoch):
            for batch, data_dict in enumerate(batch_data.train_data(batch_size)):
                feed_dict = {
                    chat_model.encoder_inputs: data_dict['x_data'],
                    chat_model.encoder_lengths: data_dict['x_data_length'],
                    chat_model.decoder_inputs: data_dict['y_data'],
                    chat_model.decoder_lengths: data_dict['y_data_length'],
                }
                # _decoder_outputs = sess.run(decoder_results['decoder_outputs'], feed_dict)
                _, decoder_result_ids_, loss_value_ = \
                    sess.run([train_op, decoder_results['decoder_result_ids'], seq_loss], feed_dict)
                if epoch % 10 == 0:
                    print('Epoch: %d, batch: %d, training loss: %.6f' % (epoch, batch, loss_value_))

            saver.save(sess, os.path.join(model_dir, 'chat'), global_step=epoch)


def main(_):
    run_train()


if __name__ == '__main__':
    tf.app.run()








