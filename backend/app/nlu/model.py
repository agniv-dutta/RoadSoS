import torch
import torch.nn as nn
from transformers import AutoModel
from torchcrf import CRF


class EmergencyNLUModel(nn.Module):
    def __init__(self, num_intents: int, num_slot_tags: int, pretrained_model: str = "xlm-roberta-base"):
        super().__init__()
        self.encoder = AutoModel.from_pretrained(pretrained_model)
        hidden_size = self.encoder.config.hidden_size

        self.intent_head = nn.Linear(hidden_size, num_intents)
        self.slot_head = nn.Linear(hidden_size, num_slot_tags)

        # CRF with batch_first=True so emissions are (batch, seq_len, num_tags)
        self.crf = CRF(num_slot_tags, batch_first=True)

        self.intent_loss_fct = nn.CrossEntropyLoss()

    def forward(self, input_ids, attention_mask, intent_labels=None, slot_labels=None):
        # encoder returns last_hidden_state (batch, seq_len, hidden)
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        hidden = outputs.last_hidden_state

        cls_hidden = hidden[:, 0, :]
        intent_logits = self.intent_head(cls_hidden)

        slot_emissions = self.slot_head(hidden)  # (batch, seq_len, num_tags)

        # decode predictions (list of list)
        with torch.no_grad():
            pred_tags = self.crf.decode(slot_emissions, mask=attention_mask.bool())

        if (intent_labels is None) and (slot_labels is None):
            return intent_logits, pred_tags

        # Compute intent loss
        intent_loss = self.intent_loss_fct(intent_logits, intent_labels)

        # Prepare tag tensor for CRF loss: CRF expects tags for masked positions only.
        # slot_labels uses -100 for ignored subword positions; build mask accordingly.
        # mask: True where attention_mask==1 and slot_labels != -100
        mask = (attention_mask.bool()) & (slot_labels != -100)

        # For positions where mask is False, fill tag value with 0 (CRF ignores them)
        tags_for_crf = slot_labels.clone()
        tags_for_crf[~mask] = 0

        # CRF returns log_likelihood; we want negative log-likelihood as loss
        crf_log_likelihood = self.crf(slot_emissions, tags_for_crf, mask=mask)
        slot_loss = -crf_log_likelihood.mean()

        loss = intent_loss + slot_loss
        return {
            "loss": loss,
            "loss_intent": intent_loss.detach(),
            "loss_slot": slot_loss.detach(),
            "intent_logits": intent_logits,
            "pred_tags": pred_tags,
        }
