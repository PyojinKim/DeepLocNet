import sys, os, torch
import shutil, argparse
import numpy as np
from include.DNN import DNN
from include.dataLoader import loadData
from pdb import set_trace as bp

#######################################################
# Save/Load Model
#######################################################
def save_best_checkpoint(state, checkpoint):
    filepath = os.path.join(checkpoint, 'best.pth')
    if not os.path.exists(checkpoint):
        print("Checkpoint Directory does not exist! Making directory {}".format(checkpoint))
        os.mkdir(checkpoint)
    torch.save(state, filepath)

def save_all_checkpoint(state, is_best, checkpoint, epoch):
    name = str(epoch)+'_stacked.pth'
    filepath = os.path.join(checkpoint, name)
    if not os.path.exists(checkpoint):
        print("Checkpoint Directory does not exist! Making directory {}".format(checkpoint))
        os.mkdir(checkpoint)
    torch.save(state, filepath)
    if is_best: shutil.copyfile(filepath, os.path.join(checkpoint, 'best.pth'))

def load_checkpoint(checkpoint, model, optimizer=None):
    if not os.path.exists(checkpoint):
        raise("File doesn't exist {}".format(checkpoint))
    checkpoint = torch.load(checkpoint)
    model.load_state_dict(checkpoint['state_dict'])

    if optimizer:
        optimizer.load_state_dict(checkpoint['optim_dict'])
    return checkpoint

def valid_model(model, validation_loader, loss_func):
    model.eval()
    totalloss = 0
    for data in validation_loader:
        output = model(data['data'].float().to(device))
        loss = loss_func(output, data['label'].float().to(device))
        totalloss += loss
    return totalloss

def get_accuracy(model, train_loader, test_loader, loss_func):
    model.eval()
    
    total = 0; correct = 0
    for batch in train_loader:
        data, labels = batch['data'].float().to(device), batch['label']
        output = model(data)
        _, predicted = torch.max(output.data, 1)
        total += labels.size(0)
        labels = np.argmax(labels, axis=1, out=None).to(device)
        correct += (predicted == labels).sum().item()
    train_accuracy = correct/total*100
    
    
    total = 0; correct = 0
    for batch in test_loader:
        data, labels = batch['data'].float().to(device), batch['label']
        output = model(data)
        _, predicted = torch.max(output.data, 1)
        total += labels.size(0)
        labels = np.argmax(labels, axis=1, out=None).to(device)
        correct += (predicted == labels).sum().item()
    test_accuracy = correct/total*100

    return train_accuracy, test_accuracy


if __name__=="__main__":

    ###########################################################
    # Parse Arguments
    ###########################################################
    parser = argparse.ArgumentParser(description='Train Classifier')
    parser.add_argument('--epoch', type=int, default=50, metavar='N', help='number of epochs (default: 50)')
    parser.add_argument('--ratio', type=float, default=0.9, metavar='N', help='train to test ratio (default: 0.8)')
    parser.add_argument('--split', type=float, default=0.1, metavar='N', help='validation split (default: 0.2)')
    parser.add_argument('--batch', type=int, default=2048, metavar='N', help='batch size (default: 2048)')
    parser.add_argument('--shuffle', type=bool, default=True, metavar='N', help='shuffle the dataset (default: True)')
    parser.add_argument('--lr', type=float, default=0.0001, metavar='N', help='learning rate (default: 0.0001)')
    parser.add_argument('--weight_decay', type=float, default=1e-5, metavar='N', help='weight decay (default: 1e-5)')
    parser.add_argument('--save', type=bool, default=False, metavar='N', help='save model (default: False)')
    
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    ###########################################################
    # Import csv and create train/validation data
    ###########################################################
    num_epoch = args.epoch
    batch_size = args.batch
    loader = loadData(batch_size, args.split, args.ratio, args.shuffle)
    dataset_size, train_loader, valid_loader, test_loader = loader.process()

    #######################################################
    # Make Model Object
    #######################################################
    model = DNN().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    loss_func = torch.nn.MSELoss()

    best_val_accuracy = 0
    # Start training
    for epoch in range(num_epoch):
        totalloss = 0
        for i, data in enumerate(train_loader):
            optimizer.zero_grad()
            output = model(data['data'].float().to(device))
            loss = loss_func(output, data['label'].float().to(device))
            loss.backward() ; optimizer.step()
            totalloss += loss.item()
            print('epoch [{:03d}/{:03d}]: completion: {:.1f} %  | batch_loss: {:.4f}'.format(epoch+1, num_epoch, i*batch_size*100/dataset_size, loss.data), end="\r")
        
        train_acc, val_acc = get_accuracy(model, train_loader, valid_loader, loss_func)
        val_loss = valid_model(model, valid_loader, loss_func)
        
        print("epoch [{:03d}/{:03d}]: train_loss: {:.4f} | val_loss: {:.4f} | train_accuracy : {:.4f} |  val_accuracy : {:.4f}".format(epoch+1, num_epoch, totalloss, val_loss, train_acc, val_acc))
        
        state = {'epoch': epoch + 1, 'state_dict': model.state_dict(), 'optim_dict' : optimizer.state_dict()}
        
        # save the best checkpoints
        if val_acc>best_val_accuracy: best = True
        save_best_checkpoint(state, checkpoint="./models/")
        if args.save: save_all_checkpoint(state, is_best=best, checkpoint="./models/", epoch=epoch)
        best = False

    
    train_acc, test_acc = get_accuracy(model, train_loader, test_loader, loss_func)
    print("train_accuracy : {:.4f} |  test_accuracy : {:.4f}".format(train_acc, test_acc))

    '''
    input = torch.tensor([100,100])
    input = input.to(device)
    model.eval()
    output = model(input.float())
    '''