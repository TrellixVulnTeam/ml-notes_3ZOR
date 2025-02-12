# Helper Functions for training
# for Pytorch projects

import pytorch_wrapper.gpu_funcs as gf

import time
import torch
import torch.nn as nn
import torch.nn.functional as F


def avg_list_tensors(tensor_list: list):
    ''' Compute mean of list of (single-value) tensors

    :param tensor_list: list of tensors
    :return: mean of values of each tensor
    '''
    return torch.stack(tensor_list).mean().item()


def compute_batch_loss(model=None, batch=None):
    ''' Compute loss on batch of data

    :param model: torch.nn.Module model
    :param batch: batch of tensors
    :return: loss
    '''
    inputs, labels = batch
    out = model(inputs)  # get predictions
    loss = F.cross_entropy(input=out, target=labels)  # compute loss
    return loss


def get_accuracy(out=None, actual=None):
    ''' Get accuracy

    :param out: model predictions of shape (batch_size,)
    :param actual: labels in a tensor of shape (batch size,)
    :return:
    '''
    _, preds = torch.max(out, dim=1)
    acc = torch.tensor(torch.sum(preds==actual).item() / len(preds))
    return acc


@torch.no_grad()
def evaluate(model=None, val_loader=None):
    ''' Without modifying gradients, evaluate validation set of images to get average loss and accuracy (over all batches in DataLoader)

    :param model: torch.nn.Module model
    :param val_loader: validation data loader (type DataLoader)
    :return: averaged validation accuracies and averaged validation losses in a dictionary in the form
        {
            'val_acc': number
            'val_loss': number
        }
    '''
    model.eval() # set to evaluate mode, i.e., layers like batch norm and dropout will work
    val_losses = []
    val_accs = []
    val_scores = {}

    for batch in val_loader:
        val_loss = compute_batch_loss(model=model, batch=batch)
        inputs, labels = batch
        out = model(inputs)
        val_accuracy = get_accuracy(out, labels)  # compute accuracy

        val_losses.append(val_loss)
        val_accs.append(val_accuracy)

    val_scores['val_loss'] = avg_list_tensors(val_losses)
    val_scores['val_acc'] = avg_list_tensors(val_accs)

    return val_scores


def train_model(model=None, epochs=10, lr=0.01, train_loader=None, val_loader=None, opt_func=torch.optim.SGD):
    ''' Train basic model

    :param model: model object that inherits from torch.nn.Module
    :param epochs: number of epochs to train for
    :param lr: learning rate
    :param train_loader: training DataLoader object
    :param val_loader: validation DataLoader object
    :param opt_func: optimization function (from torch.optim)
    :return: list of dictionaries, each element having the form for index/epoch i
        {
            'train_loss': number
            'val_acc': number
            'val_loss': number
        }
    '''
    history = []
    optimizer = opt_func(model.parameters(), lr=lr)
    start = time.time()

    for epoch in range(epochs):
        # Train
        model.train() # set to train mode
        train_losses = []

        for batch in train_loader:
            loss = compute_batch_loss(model=model, batch=batch)
            train_losses.append(loss) # add loss of current batch
            loss.backward() # backpropagate on loss
            optimizer.step() # perform single optimization step
            optimizer.zero_grad() # reset gradients to zero for future backpropagation (useful for RNNs, but not here)

        # Evaluate model after training for one additional epoch
        avg_train_loss = avg_list_tensors(train_losses)
        val_scores = evaluate(model=model, val_loader=val_loader) # get validation accuracy and loss

        # Finally, add losses and validation accuracy of current epoch to history list
        epoch_scores = {
            'train_loss': avg_train_loss,
            'val_acc': val_scores['val_acc'],
            'val_loss': val_scores['val_loss']
        }

        history.append(epoch_scores)
        print('Epoch {}/{}: Train loss={:.4f}, Val loss = {:.4f}, Val accuracy = {:.4f}'.format(
            epoch+1,
            epochs,
            avg_train_loss,
            val_scores['val_loss'],
            val_scores['val_acc']
        ))

    end = time.time() - start
    print('Total time: {:.3f} min'.format(end/60))

    return history


def predict(x=None, model=None):
    ''' Use model to make prediction on input

    :param x: batch of images in tensor
    :param model: model object that inherits from torch.nn.Module
    :return: prediction label
    '''
    device = gf.get_default_device()
    x = gf.move_to_device(data=x, device=device)
    predict_vector = model(x)
    best_pred_values, best_pred_indices = torch.max(predict_vector, dim=1)
    return best_pred_indices[0].item()
