import os
import sys
import time
import torch


def train_one_epoch(model, dataloder, criterion, optimizer, device):
    
    model.train()
    
    steps = len(dataloder.dataset) // dataloder.batch_size
    
    running_loss = 0.0
    running_cls_loss = 0.0
    running_loc_loss = 0.0
    running_corrects = 0
    
    for i, (inputs, labels, bboxes, _) in enumerate(dataloder):
        inputs, labels, bboxes = inputs.to(device), labels.to(device), bboxes.to(device)
                
        # forward
        scores, locs = model(inputs)
        _, preds = torch.max(scores, 1)
        cls_loss, loc_loss = criterion(scores, locs, labels, bboxes)        
        loss = cls_loss + 10.0 * loc_loss
        
        # backward
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        # statistics
        running_cls_loss = (running_cls_loss * i + cls_loss.item()) / (i + 1)
        running_loc_loss = (running_loc_loss * i + loc_loss.item()) / (i + 1)
        running_loss  = (running_loss * i + loss.item()) / (i + 1)
        running_corrects += torch.sum(preds == labels)
        
        # report
        sys.stdout.flush()
        sys.stdout.write("\r  Step %d/%d | Loss: %.5f (%.5f + %.5f)" % 
                         (i, steps, running_loss, running_cls_loss, running_loc_loss))
        
    epoch_loss = running_loss
    epoch_acc = running_corrects / len(dataloder.dataset)
    
    sys.stdout.flush()
    print('\r{} Loss: {:.5f} ({:.5f} + {:.5f}), Acc: {:.5f}'.format(
        '  train', epoch_loss, running_cls_loss, running_loc_loss, epoch_acc))
    
    return model

    
def validate_model(model, dataloder, criterion, device):
    model.eval()
    
    steps = len(dataloder.dataset) // dataloder.batch_size
    
    running_loss = 0.0
    running_cls_loss = 0.0
    running_loc_loss = 0.0
    running_corrects = 0
    
    with torch.no_grad():
        for i, (inputs, labels, bboxes, _) in enumerate(dataloder):
            inputs, labels, bboxes = inputs.to(device), labels.to(device), bboxes.to(device)

            # forward
            scores, locs = model(inputs)
            _, preds = torch.max(scores, 1)
            cls_loss, loc_loss = criterion(scores, locs, labels, bboxes)
            loss = cls_loss + 10.0 * loc_loss

            # statistics
            running_cls_loss = (running_cls_loss * i + cls_loss.item()) / (i + 1)
            running_loc_loss = (running_loc_loss * i + loc_loss.item()) / (i + 1)
            running_loss  = (running_loss * i + loss.item()) / (i + 1)
            running_corrects += torch.sum(preds == labels)

            # report
            sys.stdout.flush()
            sys.stdout.write("\r  Step %d/%d | Loss: %.5f (%.5f + %.5f)" % 
                             (i, steps, running_loss, running_cls_loss, running_loc_loss))
        
    epoch_loss = running_loss
    epoch_acc = running_corrects / len(dataloder.dataset)
    
    sys.stdout.flush()
    print('\r{} Loss: {:.5f} ({:.5f} + {:.5f}), Acc: {:.5f}'.format(
        '  valid', epoch_loss, running_cls_loss, running_loc_loss, epoch_acc))
    
    return epoch_acc


def train_model(model, train_dl, valid_dl, criterion, optimizer, device,
                scheduler=None, num_epochs=10):

    if not os.path.exists('models'):
        os.mkdir('models')
    
    since = time.time()
       
    best_model_wts = model.state_dict()
    best_acc = 0.0

    for epoch in range(num_epochs):
        print('Epoch {}/{}'.format(epoch + 1, num_epochs))
        print('-' * 10)

        ## train and validate
        model = train_one_epoch(model, train_dl, criterion, optimizer, device)
        val_acc = validate_model(model, valid_dl, criterion, device)
        if scheduler is not None:
            scheduler.step()

        
        # deep copy the model
        if val_acc > best_acc:
            best_acc = val_acc
            best_model_wts = model.state_dict().copy()
        torch.save(model.state_dict(), "./models/resnet50-299-epoch-{}-acc-{:.5f}.pth".format(epoch, best_acc))

        print()

    time_elapsed = time.time() - since
    print('Training complete in {:.0f}m {:.0f}s'.format(time_elapsed // 60, time_elapsed % 60))
    print('Best val Acc: {:.4f}'.format(best_acc))

    # load best model weights
    model.load_state_dict(best_model_wts)
    return model